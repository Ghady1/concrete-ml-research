"""Local HTTP boundary. SI dataclasses are the single numerical contract."""
from collections import OrderedDict
from dataclasses import asdict,replace
import hashlib,json,tempfile,uuid
from pathlib import Path
from typing import Literal,get_args
from threading import RLock

from fastapi import FastAPI,UploadFile,HTTPException,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field

from concretecalc import schemas as s,units
from concretecalc.mode_b import StrengthReport,run_mode_b
from concretecalc.mix_design import MixDesignReport,design_mix,to_mode_b_inputs
from concretecalc.calibration.dataset import CalibrationRow,load_rows
from concretecalc.calibration.fit import FitResult
from concretecalc.calibration.store import load_calibration
from concretecalc.strength import ModelConstants
from concretecalc.tables.lookups import air_content_pct
from .examples import defaults_a,defaults_b,course_examples,synthetic_csv
from .presentation import Visuals,chart_data
from .provenance import AnalysisProvenance,analysis_provenance
from .calibration_review import DiagnosticPoint,DiagnosticMetrics,partition_rows,fit_selected,diagnostics,diagnostic_metrics
from .calibration_archive import save_bundle


class Options(BaseModel):
    policy: Literal['clamp','extrapolate','raise']='extrapolate'
    normalise_age_to_28d: bool=False
    calibration_id: str | None=None


class PredictRequest(BaseModel):
    inputs: s.MixInputs
    options: Options=Field(default_factory=Options)


class DesignRequest(BaseModel):
    inputs: s.ModeAInputs
    options: Options=Field(default_factory=Options)


class PredictionResponse(BaseModel):
    schema_version: int=2
    report: StrengthReport
    visuals: Visuals
    provenance: AnalysisProvenance


class DesignResponse(BaseModel):
    schema_version: int=2
    report: MixDesignReport
    prediction: StrengthReport | None
    visuals: Visuals | None
    prediction_error: str | None=None
    provenance: AnalysisProvenance


class WorkedExample(BaseModel):
    id: str
    name: str
    description: str
    inputs: s.ModeAInputs


class Metadata(BaseModel):
    disclaimer: str
    defaults_b: s.MixInputs
    defaults_a: s.ModeAInputs
    choices: dict[str,list[str]]
    conversion_factors: dict[str,float]
    examples: list[WorkedExample]


class FitRequest(BaseModel):
    dataset_id: str
    material_set_id: str
    age_policy: Literal['only_28d','convert']='only_28d'
    accept_valid_subset: bool=False
    models: list[Literal['abrams','bolomey','feret']]=Field(default_factory=lambda: ['abrams','bolomey','feret'])
    validation_mode: Literal['in_sample','group_holdout']='in_sample'


class SaveRequest(BaseModel):
    fit_id: str
    replace_existing: bool=False


class RowIssue(BaseModel):
    row: int
    column: str
    message: str


class UploadResponse(BaseModel):
    dataset_id: str
    valid_count: int
    errors: list[RowIssue]
    rows: list[CalibrationRow]
    material_sets: list[str]
    source_name: str
    data_hash: str


class FitContext(BaseModel):
    age_policy: str
    validation_mode: str
    n_train: int
    n_held_out: int
    train_mix_ids: list[str]
    test_mix_ids: list[str]
    air_entrained: bool
    cement_type: str
    curing: str
    group_key: str='mix_id'
    split_seed: str='15'


class FitResponse(BaseModel):
    fit_id: str
    material_set_id: str
    results: dict[str,FitResult]
    diagnostics: dict[str,list[DiagnosticPoint]]
    eligible_rows: int
    excluded_rows: int
    converted_rows: int
    data_hash: str
    metrics: dict[str,dict[str,DiagnosticMetrics]]
    context: FitContext


def create_app(calibrations_dir: Path | None=None) -> FastAPI:
    """Create isolated process-local upload/fit caches; persisted fits use existing store."""
    app=FastAPI(title='Concrete Research Studio',version='0.3.0')
    directory=calibrations_dir or Path(__file__).resolve().parents[2]/'calibrations'
    datasets: OrderedDict=OrderedDict()
    fits: OrderedDict=OrderedDict()
    calibration_lock=RLock()

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request,error: RequestValidationError):
        return JSONResponse(status_code=422,content={'error':{'message':'Please check the highlighted fields.',
            'fields':[{'path':'.'.join(str(x) for x in e['loc'][1:]),'message':e['msg']} for e in error.errors()]}})

    @app.exception_handler(ValueError)
    async def domain_error(request: Request,error: ValueError):
        return JSONResponse(status_code=422,content={'error':{'message':str(error),'fields':[]}})

    @app.exception_handler(HTTPException)
    async def http_error(request: Request,error: HTTPException):
        return JSONResponse(status_code=error.status_code,content={'error':{'message':str(error.detail),'fields':[]}})

    def constants(options: Options,context_inputs: s.MixInputs | s.ModeAInputs | None=None) -> dict[str,ModelConstants] | None:
        if options.calibration_id is None:
            return None
        with calibration_lock:
            result={}
            for name in ('abrams','bolomey','feret'):
                try:
                    result[name]=load_calibration(options.calibration_id,name,directory)
                    raw=json.loads((directory/(options.calibration_id+'.json')).read_text(encoding='utf-8'))
                    context=raw['models'][name].get('fit_context',{})
                    if 'air_entrained' in context:
                        result[name]=replace(result[name],air_entrained=context['air_entrained'])
                    if context_inputs is not None:
                        for attribute in ('cement_type','curing'):
                            if attribute in context and getattr(context_inputs,attribute)!=context[attribute]:
                                raise ValueError('Saved calibration '+attribute+' differs from this mix. Select matching conditions or another parameter set.')
                except KeyError:
                    continue
                except FileNotFoundError:
                    raise HTTPException(404,'Saved calibration no longer exists. Select another set.')
            return result

    @app.get('/api/v1/health')
    def health():
        return {'status':'ok','frontend_ready':(Path(__file__).parent/'static/index.html').is_file()}

    @app.get('/api/v1/metadata',response_model=Metadata)
    def metadata():
        aliases={'shape':s.AggregateShape,'exposure':s.Exposure,'cement_type':s.CementType,
            'basis':s.WeightBasis,'curing':s.Curing,'specimen':s.Specimen,
            'element':s.ElementType,'durability':s.DurabilityClass}
        return Metadata(disclaimer=s.DISCLAIMER,defaults_b=defaults_b(),defaults_a=defaults_a(),
            choices={k:list(get_args(v)) for k,v in aliases.items()},
            conversion_factors={k:float(v) for k,v in vars(units).items() if k.isupper() and isinstance(v,(int,float))},
            examples=course_examples())

    @app.get('/api/v1/default-air')
    def default_air(nmas_mm: float,exposure: s.Exposure='moderate',air_entrained: bool=False):
        return asdict(air_content_pct(nmas_mm,exposure,air_entrained))

    @app.post('/api/v1/predict',response_model=PredictionResponse)
    def predict(body: PredictRequest):
        report=run_mode_b(body.inputs,constants(body.options,body.inputs),body.options.policy,body.options.normalise_age_to_28d)
        return PredictionResponse(report=report,visuals=chart_data(report,body.options.normalise_age_to_28d),
            provenance=analysis_provenance(asdict(body.inputs),body.options.model_dump(),report.predictions))

    @app.post('/api/v1/design',response_model=DesignResponse)
    def design(body: DesignRequest):
        report=design_mix(body.inputs,body.options.policy)
        try:
            prediction=run_mode_b(to_mode_b_inputs(report),constants(body.options,body.inputs),body.options.policy,body.options.normalise_age_to_28d)
        except ValueError as error:
            return DesignResponse(report=report,prediction=None,visuals=None,prediction_error=str(error),
                provenance=analysis_provenance(asdict(body.inputs),body.options.model_dump(),{}))
        return DesignResponse(report=report,prediction=prediction,
            visuals=chart_data(prediction,body.options.normalise_age_to_28d,report.wc.fcr.fcr_mpa),
            provenance=analysis_provenance(asdict(body.inputs),body.options.model_dump(),prediction.predictions))

    @app.get('/api/v1/calibrations')
    def list_calibrations():
        return {'items':sorted(p.stem for p in directory.glob('*.json'))}

    @app.get('/api/v1/calibrations/{material_set_id}')
    def get_calibration(material_set_id: str):
        loaded=constants(Options(calibration_id=material_set_id))
        return {name:asdict(value) for name,value in loaded.items()}

    @app.get('/api/v1/demo/calibration.csv')
    def demo_csv():
        return Response(synthetic_csv(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="synthetic-demo.csv"'})

    @app.post('/api/v1/calibration/validate',response_model=UploadResponse)
    async def validate_upload(file: UploadFile):
        payload=await file.read(10*1024*1024+1)
        await file.close()
        if len(payload)>10*1024*1024:
            raise HTTPException(413,'File exceeds the 10 MiB limit.')
        suffix=Path(file.filename or '').suffix.lower()
        if suffix not in ('.csv','.xlsx'):
            raise ValueError('Upload a CSV or .xlsx file.')
        if suffix=='.csv':
            import csv,io
            try:
                count=sum(1 for row in csv.reader(io.StringIO(payload.decode('utf-8-sig'))) if any(value.strip() for value in row))
                if count>5001:
                    raise ValueError('The limit is 5,000 rows per file.')
            except UnicodeError:
                raise ValueError('CSV must use UTF-8 encoding.')
        with tempfile.TemporaryDirectory(prefix='concrete-studio-') as temporary:
            path=Path(temporary)/('records'+suffix)
            path.write_bytes(payload)
            if suffix=='.xlsx':
                import zipfile
                try:
                    with zipfile.ZipFile(path) as archive:
                        if sum(item.file_size for item in archive.infolist())>100*1024*1024:
                            raise ValueError('Expanded workbook exceeds the supported size.')
                    from openpyxl import load_workbook
                    workbook=load_workbook(path,read_only=True,data_only=True)
                    try:
                        if workbook.worksheets[0].max_row>5001:
                            raise ValueError('Workbook exceeds 5,000 observation rows. Remove unused formatted rows if necessary.')
                    finally:
                        workbook.close()
                except (zipfile.BadZipFile,KeyError,OSError):
                    raise ValueError('The Excel file is malformed or unreadable. Save a valid .xlsx workbook and retry.')
            try:
                rows,errors=load_rows(path)
            except (OSError,UnicodeError):
                raise ValueError('The source file could not be read. Check its format and encoding.')
        if len(rows)+len({e[0] for e in errors if e[0]>1})>5000:
            raise ValueError('The limit is 5,000 rows per file.')
        key=uuid.uuid4().hex
        datasets[key]={'rows':rows,'errors':errors,'name':file.filename,'hash':hashlib.sha256(payload).hexdigest()}
        while len(datasets)>8:
            datasets.popitem(last=False)
        return {'dataset_id':key,'valid_count':len(rows),'errors':[{'row':r,'column':c,'message':m} for r,c,m in errors],
            'rows':[asdict(row) for row in rows],'material_sets':sorted({r.material_set_id for r in rows}),
            'source_name':file.filename,'data_hash':datasets[key]['hash']}

    @app.post('/api/v1/calibration/fit',response_model=FitResponse)
    def fit(body: FitRequest):
        data=datasets.get(body.dataset_id)
        if data is None:
            raise HTTPException(404,'Upload expired or server restarted. Upload the source file again.')
        if data['errors'] and not body.accept_valid_subset:
            raise ValueError('Review the errors and explicitly allow fitting only valid rows.')
        rows=tuple(row for row in data['rows'] if row.material_set_id==body.material_set_id)
        eligible=tuple(row for row in rows if body.age_policy=='convert' or row.age_days==28)
        for attribute in ('air_entrained','cement_type','curing'):
            if len({getattr(row,attribute) for row in eligible})>1:
                raise ValueError('Fit one '+attribute+' condition at a time; separate material_set_id values for incompatible conditions.')
        train,test=partition_rows(eligible,body.validation_mode)
        results=fit_selected(train,body.age_policy,body.models)
        test_ids={row.mix_id for row in test}
        points=diagnostics(eligible,body.age_policy,results,test_ids)
        metrics={}
        for name,values in points.items():
            metrics[name]={}
            for split in ('calibration','held_out'):
                selected=[value for value in values if value.split==split]
                if selected:
                    metrics[name][split]=diagnostic_metrics(selected)
        context=FitContext(age_policy=body.age_policy,validation_mode=body.validation_mode,
            n_train=len(train),n_held_out=len(test),train_mix_ids=sorted({row.mix_id for row in train}),test_mix_ids=sorted(test_ids),
            air_entrained=eligible[0].air_entrained,cement_type=eligible[0].cement_type,curing=eligible[0].curing)
        key=uuid.uuid4().hex
        fits[key]={'dataset_id':body.dataset_id,'material':body.material_set_id,'results':results,'data':data,'context':context.model_dump()}
        while len(fits)>16:
            fits.popitem(last=False)
        return FitResponse(fit_id=key,material_set_id=body.material_set_id,results=results,
            diagnostics=points,metrics=metrics,context=context,eligible_rows=len(eligible),excluded_rows=len(rows)-len(eligible),
            converted_rows=sum(row.age_days!=28 for row in eligible),data_hash=data['hash'])

    @app.post('/api/v1/calibration/save')
    def save(body: SaveRequest):
        fit=fits.get(body.fit_id)
        if fit is None:
            raise HTTPException(404,'Fit expired. Fit the selected dataset again.')
        if fit['dataset_id'] not in datasets:
            raise HTTPException(404,'Source upload expired. Re-upload and fit before saving.')
        try:
            with calibration_lock:
                return save_bundle(fit['material'],fit['results'],fit['data']['name'],fit['data']['hash'],
                    fit['context'],directory,body.replace_existing)
        except FileExistsError as error:
            raise HTTPException(409,str(error))

    static=Path(__file__).parent/'static'
    if (static/'index.html').is_file():
        app.mount('/',StaticFiles(directory=static,html=True),name='frontend')
    return app
