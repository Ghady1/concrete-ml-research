"""Transparent fitting/holdout presentation using existing engine models."""
import hashlib
from typing import Literal
import numpy as np
from pydantic import BaseModel
from concretecalc import schemas as s
from concretecalc.calibration.dataset import CalibrationRow,rows_to_fit_arrays
from concretecalc.calibration.fit import fit_abrams,fit_bolomey,fit_feret,FitResult
from concretecalc.moisture import aggregate_moisture,effective_water
from concretecalc.volumes import volume_check
from concretecalc.strength import MixState,ModelConstants
from concretecalc.strength.registry import MODEL_REGISTRY,default_constants


class DiagnosticPoint(BaseModel):
    mix_id: str
    measured_mpa: float
    predicted_mpa: float
    default_mpa: float | None
    residual_mpa: float
    split: Literal['calibration','held_out']


class DiagnosticMetrics(BaseModel):
    n: int
    mae_mpa: float
    rmse_mpa: float
    r2_mpa: float | None
    default_rmse_mpa: float | None


def partition_rows(rows: tuple[CalibrationRow,...], mode: str) -> tuple[tuple[CalibrationRow,...],tuple[CalibrationRow,...]]:
    """Fixed group split by mix_id; project guard: >=10 unique mixes, >=2 held out."""
    if mode == 'in_sample':
        return rows, ()
    if mode != 'group_holdout':
        raise ValueError('Unknown validation mode')
    groups = sorted({row.mix_id for row in rows}, key=lambda name: hashlib.sha256(('15:'+name).encode('utf-8')).hexdigest())
    if len(groups) < 10:
        raise ValueError('Grouped holdout requires at least 10 distinct mix_id values. Repeated ages or cylinders are not independent mixes.')
    test_count = max(2,len(groups)//5)
    held_out = set(groups[:test_count])
    return tuple(row for row in rows if row.mix_id not in held_out), tuple(row for row in rows if row.mix_id in held_out)


def fit_selected(rows: tuple[CalibrationRow,...], age_policy: str, models: list[str]) -> dict[str,FitResult]:
    """Fit only selected parametric equations, on calibration rows only."""
    arrays = rows_to_fit_arrays(rows,age_policy)
    functions = {'abrams':(fit_abrams,arrays.wc),'bolomey':(fit_bolomey,arrays.cw),'feret':(fit_feret,arrays.volume_ratio)}
    if not models or len(set(models)) != len(models) or set(models)-set(functions):
        raise ValueError('Choose at least one supported model, without duplicates.')
    return {name:functions[name][0](functions[name][1],arrays.strength_mpa) for name in models}


def diagnostics(rows: tuple[CalibrationRow,...], age_policy: str, results: dict[str,FitResult], test_ids: set[str]) -> dict[str,list[DiagnosticPoint]]:
    arrays = rows_to_fit_arrays(rows,age_policy)
    points = {name:[] for name in results}
    for row,measured in zip(rows,arrays.strength_mpa):
        coarse = aggregate_moisture('CA',row.ca_kg_m3,row.weight_basis,row.ca_absorption_pct,row.ca_mc_pct)
        fine = aggregate_moisture('FA',row.fa_kg_m3,row.weight_basis,row.fa_absorption_pct,row.fa_mc_pct)
        water = effective_water(row.water_kg_m3,coarse,fine).effective_water_kg
        volumes = volume_check((s.Binder('cement',row.cement_kg_m3,row.cement_sg,'cement'),),water,
            coarse.ssd_kg,row.ca_sg_ssd,fine.ssd_kg,row.fa_sg_ssd,row.air_pct)
        state = MixState(row.cement_kg_m3,row.cement_kg_m3,water,water/row.cement_kg_m3,water/row.cement_kg_m3,
            row.air_pct,row.air_entrained,volumes.cement_m3,volumes.water_m3,volumes.air_m3,row.cement_type,row.curing,28)
        for name,result in results.items():
            constants = ModelConstants(name,'in_memory_fit',result.values,'Fit for diagnostics; not saved',False,None,28)
            predicted = MODEL_REGISTRY[name](state,constants).mean_28d_mpa
            default = MODEL_REGISTRY[name](state,default_constants(name,row.air_entrained)).mean_28d_mpa
            if predicted is None:
                raise ValueError('Fitted model prediction is unavailable')
            points[name].append(DiagnosticPoint(mix_id=row.mix_id,measured_mpa=float(measured),predicted_mpa=predicted,
                default_mpa=default,residual_mpa=float(measured)-predicted,split='held_out' if row.mix_id in test_ids else 'calibration'))
    return points


def diagnostic_metrics(points: list[DiagnosticPoint]) -> DiagnosticMetrics:
    if not points:
        raise ValueError('No observations for diagnostics')
    residuals = np.array([point.residual_mpa for point in points])
    measured = np.array([point.measured_mpa for point in points])
    total = float(np.sum((measured-np.mean(measured))**2))
    default = [point.measured_mpa-point.default_mpa for point in points if point.default_mpa is not None]
    return DiagnosticMetrics(n=len(points),mae_mpa=float(np.mean(np.abs(residuals))),
        rmse_mpa=float(np.sqrt(np.mean(residuals**2))),r2_mpa=None if total==0 else 1-float(np.sum(residuals**2))/total,
        default_rmse_mpa=float(np.sqrt(np.mean(np.array(default)**2))) if len(default)==len(points) else None)
