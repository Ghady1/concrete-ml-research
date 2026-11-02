"""Full-precision SI chart data assembled only from existing engine functions."""
from pydantic import BaseModel
from concretecalc.mode_b import StrengthReport
from concretecalc.strength.age import strength_at_age_mpa
from concretecalc.tables.lookups import slump_limits_mm


class Point(BaseModel):
    name: str
    value: float | None


class AgePoint(BaseModel):
    age_days: float
    values: dict[str,float | None]


class Visuals(BaseModel):
    strengths: list[Point]
    water: list[Point]
    volumes: list[Point]
    ages: list[AgePoint]
    required_mean_mpa: float | None = None
    table_wc_min: float
    table_wc_max: float
    curve_policy: str = 'extrapolate'
    slump_element_range_mm: tuple[float, float] | None = None


def chart_data(report: StrengthReport,normalized: bool=False,required_mean_mpa: float | None=None) -> Visuals:
    """Use reported masses/volumes and existing age equation; no fitted averages."""
    maximum=max(90,report.inputs.age_days)
    days=sorted({1.,7.,14.,28.,56.,90.,float(report.inputs.age_days),
                 *(1+(maximum-1)*i/99 for i in range(100))})
    ages=[]
    for day in days:
        values={}
        for name,prediction in report.predictions.items():
            mean=prediction.mean_28d_mpa
            values[name]=None if mean is None or mean<=0 else strength_at_age_mpa(
                mean,day,report.inputs.cement_type,report.inputs.curing,normalized).strength_mpa
        ages.append(AgePoint(age_days=day,values=values))
    points = report.plot.aci_ae_points if report.inputs.air_entrained else report.plot.aci_non_ae_points
    element_range = None
    if report.inputs.element is not None:
        lower, upper = slump_limits_mm(report.inputs.element)
        if lower.value is not None and upper.value is not None:
            element_range = (lower.value, upper.value)
    return Visuals(table_wc_min=min(point[0] for point in points), table_wc_max=max(point[0] for point in points),
        slump_element_range_mm=element_range,
        strengths=[Point(name=name,value=p.mean_28d_mpa) for name,p in report.predictions.items()],
        water=[Point(name='Added water',value=report.water.added_water_kg),
            Point(name='Coarse free water',value=report.water.free_water_ca_kg),
            Point(name='Fine free water',value=report.water.free_water_fa_kg),
            Point(name='Effective water',value=report.water.effective_water_kg)],
        volumes=[Point(name=name,value=getattr(report.volumes,field)) for name,field in
            [('Cement','cement_m3'),('SCM','scm_m3'),('Water','water_m3'),
             ('Coarse','coarse_m3'),('Fine','fine_m3'),('Air','air_m3')]],
        ages=ages,required_mean_mpa=required_mean_mpa)
