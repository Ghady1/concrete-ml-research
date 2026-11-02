"""Calibration JSON persistence boundary; pure models never read these files."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import uuid

from concretecalc.calibration.fit import FitResult
from concretecalc.strength import ModelConstants


def _path(material_set_id: str, directory: Path) -> Path:
    """Restrict material identifiers to file-name labels, preventing traversal."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',material_set_id):
        raise ValueError('material_set_id must contain only letters, digits, dots, underscores or hyphens')
    return Path(directory)/f'{material_set_id}.json'


def file_sha256(path: str | Path) -> str:
    """SHA-256 of exact source bytes, independent of filename or newline style."""
    digest=hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(65536),b''):
            digest.update(block)
    return digest.hexdigest()


def _validate_values(model_name: str, values: dict) -> None:
    """Require the known finite positive parameter set before storing/loading."""
    expected={'abrams':{'A','B'},'bolomey':{'K'},'feret':{'K'}}
    if model_name not in expected or set(values)!=expected[model_name]:
        raise ValueError('Unknown model or mismatched constants')
    for value in values.values():
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
            raise ValueError('Calibration constants must be finite and positive')
    if model_name=='abrams' and values['B']<=1:
        raise ValueError('Abrams B must exceed 1')


def save_calibration(material_set_id: str, model_name: str, result: FitResult,
                      source_csv: str, data_hash: str,
                      directory: Path=Path('calibrations')) -> Path:
    """Atomically merge a model into one material-set JSON; timestamp at I/O boundary."""
    path=_path(material_set_id,directory)
    if result.model_name!=model_name or result.n_rows<3:
        raise ValueError('Calibration model must match a fit of >=3 rows')
    _validate_values(model_name,result.values)
    raw={'material_set_id':material_set_id,'models':{}}
    if path.exists():
        raw=json.loads(path.read_text(encoding='utf-8'))
        if raw.get('material_set_id')!=material_set_id or not isinstance(raw.get('models'),dict):
            raise ValueError('Malformed calibration material-set file')
    stats=asdict(result)
    raw['models'][model_name]={'model':model_name,'constants':dict(result.values),
        'fit_stats':{key:stats[key] for key in ('r2','r2_space','r2_mpa','rmse_mpa')},
        'n_rows':result.n_rows,'source_csv':source_csv,'data_hash':data_hash,
        'created_utc':datetime.now(timezone.utc).isoformat()}
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(raw,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(temporary,path)
    return path


def load_calibration(material_set_id: str, model_name: str,
                      directory: Path=Path('calibrations')) -> ModelConstants:
    """Load stored 28-day parameters with calibrated=True and source provenance."""
    path=_path(material_set_id,directory)
    raw=json.loads(path.read_text(encoding='utf-8'))
    if raw.get('material_set_id')!=material_set_id:
        raise ValueError('Calibration material_set_id mismatch')
    entry=raw['models'][model_name]
    if entry['model']!=model_name or entry['n_rows']<3:
        raise ValueError('Invalid stored fit')
    _validate_values(model_name,entry['constants'])
    source=f"Material set {material_set_id}; source {entry['source_csv']}; SHA-256 {entry['data_hash']}; created {entry['created_utc']}"
    return ModelConstants(model_name,'calibrated',dict(entry['constants']),source,
                           True,None,28,material_set_id)
