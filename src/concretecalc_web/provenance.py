"""Version fingerprints at the application boundary; no numerical engine changes."""
from datetime import datetime, timezone
from functools import lru_cache
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
import platform
from pydantic import BaseModel
import concretecalc


class AnalysisProvenance(BaseModel):
    application_version: str = '0.3.0'
    engine_package_version: str
    engine_sha256: str
    reference_sha256: str
    parameter_sha256: str
    input_settings_sha256: str
    created_utc: str
    python_version: str


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


@lru_cache(maxsize=1)
def runtime_fingerprints() -> tuple[str, str, str]:
    """Hash sorted engine source/data paths and bytes; stable within this process."""
    root = Path(concretecalc.__file__).parent
    hashes = []
    for pattern in ('*.py', '*.json'):
        digest = hashlib.sha256()
        for path in sorted(root.rglob(pattern)):
            digest.update(path.relative_to(root).as_posix().encode('utf-8'))
            digest.update(b'\0')
            digest.update(path.read_bytes())
            digest.update(b'\0')
        hashes.append(digest.hexdigest())
    return version('concrete-ml-research'), hashes[0], hashes[1]


def analysis_provenance(inputs: dict, options: dict, predictions: dict) -> AnalysisProvenance:
    """Fingerprint exactly submitted canonical inputs/settings and returned parameters."""
    package, engine, references = runtime_fingerprints()
    parameters = {name: {'values': item.constants_used, 'source': item.constants_source,
                         'calibrated': item.calibrated} for name, item in predictions.items()}
    return AnalysisProvenance(engine_package_version=package, engine_sha256=engine,
        reference_sha256=references, parameter_sha256=_digest(parameters),
        input_settings_sha256=_digest({'inputs': inputs, 'options': options}),
        created_utc=datetime.now(timezone.utc).isoformat(), python_version=platform.python_version())
