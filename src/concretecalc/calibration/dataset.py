"""Stable SI CSV/Excel schema, task section 10; row errors never print.

Error row numbers include the header (first observation=2). Optional extra
cube_to_cylinder_factor supports the explicit conversion required by Q4.
"""
from dataclasses import dataclass, fields
from datetime import date, datetime
from pathlib import Path
from typing import Literal
import math
import numpy as np
import pandas as pd

from concretecalc import schemas as s
from concretecalc.validation import _choice, validate_mode_b
from concretecalc.tables.lookups import input_validation_limits
from concretecalc.moisture import aggregate_moisture, effective_water
from concretecalc.volumes import absolute_volume_m3
from concretecalc.strength.age import age_factor
from concretecalc.calibration.fit import FitArrays


@dataclass(frozen=True)
class CalibrationRow:
    """One measured mix at one age; kg/m3, mm, MPa, days and percent."""
    mix_id: str
    material_set_id: str
    cement_kg_m3: float
    water_kg_m3: float
    ca_kg_m3: float
    fa_kg_m3: float
    weight_basis: s.WeightBasis
    cement_sg: float
    cement_type: s.CementType
    ca_sg_ssd: float
    ca_drd_kg_m3: float
    ca_absorption_pct: float
    ca_mc_pct: float
    nmas_mm: float
    ca_shape: s.AggregateShape
    fa_sg_ssd: float
    fa_absorption_pct: float
    fa_mc_pct: float
    fa_fm: float
    air_pct: float
    air_entrained: bool
    curing: s.Curing
    age_days: float
    specimen: s.Specimen
    n_specimens: int
    measured_strength_mpa: float
    strength_std_mpa: float | None
    measured_slump_mm: float
    test_date: str
    notes: str
    cube_to_cylinder_factor: float | None = None


CSV_COLUMNS=tuple(f.name for f in fields(CalibrationRow) if f.name!='cube_to_cylinder_factor')
RESERVED_COLUMNS=('scm_name','scm_pct','scm_sg','sp_kg_m3')
_TEXT=('mix_id','material_set_id','weight_basis','cement_type','ca_shape','curing','specimen','test_date','notes')
_ALIASES={'weight_basis':s.WeightBasis,'cement_type':s.CementType,
          'ca_shape':s.AggregateShape,'curing':s.Curing,'specimen':s.Specimen}


def _row_inputs(row: CalibrationRow) -> s.MixInputs:
    """Use explicit measured air; exposure is irrelevant to its default lookup."""
    return s.MixInputs(s.Binder('cement',row.cement_kg_m3,row.cement_sg,'cement'),
        row.water_kg_m3,row.ca_kg_m3,s.CoarseAggregateProperties(row.ca_sg_ssd,
        row.ca_drd_kg_m3,row.ca_absorption_pct,row.ca_mc_pct,row.ca_shape),
        row.fa_kg_m3,s.FineAggregateProperties(row.fa_sg_ssd,row.fa_absorption_pct,
        row.fa_mc_pct,row.fa_fm),row.nmas_mm,row.weight_basis,row.air_entrained,'moderate',
        cement_type=row.cement_type,air_pct=row.air_pct,curing=row.curing,
        age_days=row.age_days,specimen=row.specimen,cube_to_cylinder_factor=row.cube_to_cylinder_factor)


def _parse_cell(column: str, value: object, limits: dict[str,float]) -> object:
    """Validate one cell independently so errors in other cells are retained."""
    text=str(value).strip()
    if column in _TEXT:
        if column=='test_date' and isinstance(value,datetime):
            text=value.date().isoformat()
        elif column=='test_date' and isinstance(value,date):
            text=value.isoformat()
        if column!='notes' and not text:
            raise ValueError('value is required')
        if column in _ALIASES:
            _choice(text,_ALIASES[column],column)
        if column=='test_date':
            date.fromisoformat(text)
        return text
    if column=='air_entrained':
        if text.lower() in ('true','1'):
            return True
        if text.lower() in ('false','0'):
            return False
        raise ValueError('expected true/false or 1/0')
    if column in ('strength_std_mpa','cube_to_cylinder_factor') and not text:
        return None
    number=float(text)
    if not math.isfinite(number):
        raise ValueError('must be finite')
    nonnegative=('ca_absorption_pct','ca_mc_pct','fa_absorption_pct','fa_mc_pct',
                 'air_pct','strength_std_mpa','measured_slump_mm')
    if number<0 or (column not in nonnegative and number==0):
        raise ValueError('must be nonnegative' if column in nonnegative else 'must be positive')
    if column.endswith('absorption_pct') and number>limits['hard.absorption_pct.max']:
        raise ValueError('absorption exceeds hard maximum')
    if column in ('ca_mc_pct','fa_mc_pct') and number>limits['hard.mc_pct.max']:
        raise ValueError('moisture exceeds hard maximum')
    if column=='air_pct' and number>=100:
        raise ValueError('must be below 100 percent')
    if column=='age_days' and number<limits['hard.age_days.min']:
        raise ValueError('age must be at least one day')
    if column=='n_specimens':
        if not number.is_integer():
            raise ValueError('must be an integer')
        return int(number)
    return number


def load_rows(path: str | Path) -> tuple[tuple[CalibrationRow,...],tuple[tuple[int,str,str],...]]:
    """Read SI CSV or .xlsx; return valid rows and all (row,column,error)."""
    path=Path(path)
    if path.suffix.lower()=='.xlsx':
        frame=pd.read_excel(path,dtype=object,keep_default_na=False,engine='openpyxl')
    elif path.suffix.lower()=='.csv':
        frame=pd.read_csv(path,dtype=object,keep_default_na=False,encoding='utf-8-sig')
    else:
        raise ValueError('Calibration file must be CSV or Excel (.xlsx)')
    required=set(CSV_COLUMNS)-{'strength_std_mpa'}
    errors=[(1,column,'required column missing') for column in sorted(required-set(frame.columns))]
    if errors:
        return (),tuple(errors)
    rows=[]
    limits=input_validation_limits()
    for index,raw in enumerate(frame.to_dict(orient='records'),start=2):
        values={}
        row_errors=[]
        for column in (*CSV_COLUMNS,'cube_to_cylinder_factor'):
            try:
                values[column]=_parse_cell(column,raw.get(column,''),limits)
            except (ValueError,TypeError,OverflowError) as error:
                row_errors.append((index,column,str(error)))
        if values.get('specimen')=='cube_150' and values.get('cube_to_cylinder_factor') is None:
            row_errors.append((index,'cube_to_cylinder_factor','cube measurement requires an explicit conversion factor'))
        if not row_errors:
            row=CalibrationRow(**values)
            try:
                validate_mode_b(_row_inputs(row))
                rows_to_fit_arrays((row,),'convert')
            except ValueError as error:
                row_errors.append((index,'inputs',str(error)))
            if not row_errors:
                rows.append(row)
        errors.extend(row_errors)
    return tuple(rows),tuple(errors)


def rows_to_fit_arrays(rows: tuple[CalibrationRow,...],
                        age_policy: Literal['only_28d','convert']='only_28d') -> FitArrays:
    """Correct aggregate water, convert cubes and optionally measured age to 28d."""
    if age_policy not in ('only_28d','convert'):
        raise ValueError('Unknown age_policy')
    if len({row.material_set_id for row in rows})>1:
        raise ValueError('Fit one material_set_id at a time')
    wc_values,ratios,strengths=[],[],[]
    for row in rows:
        validate_mode_b(_row_inputs(row))
        if age_policy=='only_28d' and row.age_days!=28:
            continue
        coarse=aggregate_moisture('CA',row.ca_kg_m3,row.weight_basis,row.ca_absorption_pct,row.ca_mc_pct)
        fine=aggregate_moisture('FA',row.fa_kg_m3,row.weight_basis,row.fa_absorption_pct,row.fa_mc_pct)
        water=effective_water(row.water_kg_m3,coarse,fine).effective_water_kg
        if water<=0:
            raise ValueError(f'{row.mix_id}: effective water must be positive')
        measured=row.measured_strength_mpa
        if row.specimen=='cube_150':
            if row.cube_to_cylinder_factor is None:
                raise ValueError('cube_to_cylinder_factor is required')
            measured*=row.cube_to_cylinder_factor
        if age_policy=='convert' and row.age_days!=28:
            measured/=age_factor(row.age_days,row.cement_type,row.curing)[0]
        vc=absolute_volume_m3(row.cement_kg_m3,row.cement_sg)
        vw=absolute_volume_m3(water,1)
        wc_values.append(water/row.cement_kg_m3)
        ratios.append(vc/(vc+vw+row.air_pct/100))
        strengths.append(measured)
    wc=np.array(wc_values,dtype=float)
    cw=1/wc
    ratio=np.array(ratios,dtype=float)
    strength=np.array(strengths,dtype=float)
    for array in (wc,cw,ratio,strength):
        array.flags.writeable=False
    return FitArrays(wc,cw,ratio,strength)
