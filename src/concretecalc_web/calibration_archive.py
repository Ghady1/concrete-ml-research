"""Atomically save one parameter bundle, retaining previous model records."""
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime,timezone
from concretecalc.calibration.fit import FitResult
from concretecalc.calibration.store import save_calibration,_path


def save_bundle(material: str, results: dict[str,FitResult], source: str, data_hash: str,
                context: dict, directory: Path, replace_existing: bool) -> dict:
    target = _path(material,directory)
    existing = json.loads(target.read_text(encoding='utf-8')) if target.exists() else None
    if existing is not None and not replace_existing:
        raise FileExistsError('This material set already exists. Explicitly allow a new saved revision or use a new material_set_id.')
    directory.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='parameter-save-',dir=directory) as temporary:
        stage = Path(temporary)
        if existing is not None:
            (stage/target.name).write_text(json.dumps(existing,allow_nan=False),encoding='utf-8')
        for name,result in results.items():
            saved = save_calibration(material,name,result,source,data_hash,stage)
        raw = json.loads(saved.read_text(encoding='utf-8'))
        history = list(raw.get('revision_history',[]))
        if existing is not None:
            history.append({'archived_utc':datetime.now(timezone.utc).isoformat(),'models':existing['models']})
        raw['revision_history'] = history
        for name in results:
            raw['models'][name]['fit_context'] = context
        raw['revision'] = int((existing or {}).get('revision',0))+1
        saved.write_text(json.dumps(raw,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        os.replace(saved,target)
    return {'material_set_id':material,'saved_models':list(results),'revision':raw['revision']}
