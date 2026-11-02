"""Local HTTP boundary. SI dataclasses are the single numerical contract."""
from collections import OrderedDict
from dataclasses import asdict,replace
import hashlib,json,tempfile,uuid
from pathlib import Path
from typing import Literal,get_args

from fastapi import FastAPI,UploadFile,HTTPException,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field

from concretecalc import schemas as s,units
from concretecalc.mode_b import StrengthReport,run_mode_b
from concretecalc.mix_design import MixDesignReport,design_mix,to_mode_b_inputs
from concretecalc.calibration.dataset import load_rows,rows_to_fit_arrays,_row_inputs
from concretecalc.calibration.fit import FitResult,fit_all
from concretecalc.calibration.store import save_calibration,load_calibration
from concretecalc.strength import ModelConstants,MixState
from concretecalc.strength.registry import MODEL_REGISTRY
from concretecalc.moisture import aggregate_moisture,effective_water
from concretecalc.volumes import absolute_volume_m3
from concretecalc.tables.lookups import air_content_pct
from .examples import defaults_a,defaults_b,course_examples,synthetic_csv
from .presentation import Visuals,chart_data


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
    schema_version: int=1
    report: StrengthReport
    visuals: Visuals


class DesignResponse(BaseModel):
    schema_version: int=1
    report: MixDesignReport
    prediction: StrengthReport | None
    visuals: Visuals | None
    prediction_error: str | None=None


class Metadata(BaseModel):
    disclaimer: str
    defaults_b: s.MixInputs
    defaults_a: s.ModeAInputs
    choices: dict[str,list[str]]
    conversion_factors: dict[str,float]
    examples: list[dict]


class FitRequest(BaseModel):
    dataset_id: str
    material_set_id: str
    age_policy: Literal['only_28d','convert']='only_28d'
    accept_valid_subset: bool=False


class SaveRequest(BaseModel):
    fit_id: str


def create_app(calibrations_dir: Path | None=None) -> FastAPI:
    """Create isolated process-local upload/fit caches; persisted fits use existing store."""
    app=FastAPI(title='Concrete Research Studio',version='0.2.0')
    directory=calibrations_dir or Path(__file__).resolve().parents[2]/'calibrations'
    datasets: OrderedDict=OrderedDict()
    fits: OrderedDict=OrderedDict()

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

    def constants(options: Options) -> dict[str,ModelConstants] | None:
        if options.calibration_id is None:
            return None
        result={}
        for name in ('abrams','bolomey','feret'):
            try:
                result[name]=load_calibration(options.calibration_id,name,directory)
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
        report=run_mode_b(body.inputs,constants(body.options),body.options.policy,body.options.normalise_age_to_28d)
        return PredictionResponse(report=report,visuals=chart_data(report,body.options.normalise_age_to_28d))

    @app.post('/api/v1/design',response_model=DesignResponse)
    def design(body: DesignRequest):
        report=design_mix(body.inputs,body.options.policy)
        try:
            prediction=run_mode_b(to_mode_b_inputs(report),constants(body.options),body.options.policy,body.options.normalise_age_to_28d)
        except ValueError as error:
            return DesignResponse(report=report,prediction=None,visuals=None,prediction_error=str(error))
        return DesignResponse(report=report,prediction=prediction,
            visuals=chart_data(prediction,body.options.normalise_age_to_28d,report.wc.fcr.fcr_mpa))

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

    @app.post('/api/v1/calibration/validate')
    async def validate_upload(file: UploadFile):
        payload=await file.read(10*1024*1024+1)
        await file.close()
        if len(payload)>10*1024*1024:
            raise HTTPException(413,'File exceeds the 10 MiB limit.')
        suffix=Path(file.filename or '').suffix.lower()
        if suffix not in ('.csv','.xlsx'):
            raise ValueError('Upload a CSV or .xlsx file.')
        with tempfile.TemporaryDirectory(prefix='concrete-studio-') as temporary:
            path=Path(temporary)/('records'+suffix)
            path.write_bytes(payload)
            if suffix=='.xlsx':
                import zipfile
                with zipfile.ZipFile(path) as archive:
                    if sum(item.file_size for item in archive.infolist())>100*1024*1024:
                        raise ValueError('Expanded workbook exceeds the supported size.')
            rows,errors=load_rows(path)
        if len(rows)+len({e[0] for e in errors if e[0]>1})>5000:
            raise ValueError('The limit is 5,000 rows per file.')
        key=uuid.uuid4().hex
        datasets[key]={'rows':rows,'errors':errors,'name':file.filename,'hash':hashlib.sha256(payload).hexdigest()}
        while len(datasets)>8:
            datasets.popitem(last=False)
        return {'dataset_id':key,'valid_count':len(rows),'errors':[{'row':r,'column':c,'message':m} for r,c,m in errors],
            'rows':[asdict(row) for row in rows],'material_sets':sorted({r.material_set_id for r in rows}),
            'source_name':file.filename,'data_hash':datasets[key]['hash']}

    @app.post('/api/v1/calibration/fit')
    def fit(body: FitRequest):
        data=datasets.get(body.dataset_id)
        if data is None:
            raise HTTPException(404,'Upload expired or server restarted. Upload the source file again.')
        if data['errors'] and not body.accept_valid_subset:
            raise ValueError('Review the errors and explicitly allow fitting only valid rows.')
        rows=tuple(row for row in data['rows'] if row.material_set_id==body.material_set_id)
        arrays=rows_to_fit_arrays(rows,body.age_policy)
        results=fit_all(arrays)
        diagnostics={name:[] for name in results}
        eligible=[row for row in rows if body.age_policy=='convert' or row.age_days==28]
        for row,measured in zip(eligible,arrays.strength_mpa):
            report=run_mode_b(_row_inputs(row))
            state=MixState(report.cement_kg_m3,report.cement_kg_m3,report.water.effective_water_kg,
                report.wc,report.wcm,report.air_pct,row.air_entrained,report.volumes.cement_m3,
                report.volumes.water_m3,report.volumes.air_m3,row.cement_type,row.curing,28)
            for name,result in results.items():
                parameters=ModelConstants(name,'in_memory_fit',result.values,'In-sample fit; not saved',False,None,28)
                predicted=MODEL_REGISTRY[name](state,parameters).mean_28d_mpa
                diagnostics[name].append({'mix_id':row.mix_id,'measured_mpa':float(measured),
                    'predicted_mpa':predicted,'residual_mpa':float(measured)-predicted})
        key=uuid.uuid4().hex
        fits[key]={'dataset_id':body.dataset_id,'material':body.material_set_id,'results':results,'data':data}
        while len(fits)>16:
            fits.popitem(last=False)
        return {'fit_id':key,'material_set_id':body.material_set_id,'results':{n:asdict(r) for n,r in results.items()},
            'diagnostics':diagnostics,'eligible_rows':len(eligible),'excluded_rows':len(rows)-len(eligible),
            'converted_rows':sum(r.age_days!=28 for r in eligible),'data_hash':data['hash']}

    @app.post('/api/v1/calibration/save')
    def save(body: SaveRequest):
        fit=fits.get(body.fit_id)
        if fit is None:
            raise HTTPException(404,'Fit expired. Fit the selected dataset again.')
        if fit['dataset_id'] not in datasets:
            raise HTTPException(404,'Source upload expired. Re-upload and fit before saving.')
        for name,result in fit['results'].items():
            save_calibration(fit['material'],name,result,fit['data']['name'],fit['data']['hash'],directory)
        return {'material_set_id':fit['material'],'saved_models':list(fit['results'])}

    static=Path(__file__).parent/'static'
    if (static/'index.html').is_file():
        app.mount('/',StaticFiles(directory=static,html=True),name='frontend')
    return app
