"""Documented course examples and explicitly synthetic calibration fixture."""
from dataclasses import asdict
import csv,io
import numpy as np
from concretecalc.schemas import Binder,CoarseAggregateProperties,FineAggregateProperties,MixInputs,ModeAInputs
from concretecalc.calibration.dataset import CSV_COLUMNS
from concretecalc.mix_design import step7_fine


def defaults_b() -> MixInputs:
    """A consistent SSD-conditioned example, entered as stockpile masses."""
    return MixInputs(Binder('Portland cement',315,3.15,'cement'),200,1060,
        CoarseAggregateProperties(2.65,1600,1,1,'angular'),728,
        FineAggregateProperties(2.6,1,1,2.6),19,'as_received',False,'moderate',air_pct=None,
        element='building_columns')


def defaults_a() -> ModeAInputs:
    b=defaults_b()
    return ModeAInputs(25,'building_columns','moderate',False,3.15,b.coarse,b.fine,nmas_mm=19)


def course_examples() -> list[dict]:
    first=ModeAInputs(20.68427187,'reinforced_foundation_walls_footings','moderate',False,3.15,
        CoarseAggregateProperties(2.69,1681.93865385,.8,2,'angular'),
        FineAggregateProperties(2.65,6,8,2.6),nmas_mm=37.5)
    second=ModeAInputs(24.1,'building_columns','severe',True,3.15,
        CoarseAggregateProperties(2.62,1681,.4,1.5,'round_gravel'),
        FineAggregateProperties(2.57,.8,4,2.6),sigma_mpa=2.4,n_samples=31,
        nmas_mm=25,durability_class='freeze_thaw_moist')
    return [{'id':'foundation','name':'A foundation, from first principles','description':'3000 psi course example; non-air-entrained, nominal 37.5 mm aggregate. Missing-input assumptions are documented.','inputs':asdict(first)},
        {'id':'bridge-pier','name':'When exposure governs','description':'24.1 MPa bridge-pier course example; severe freeze-thaw, 25 mm NMAS. Minimum cement and durability warnings remain visible.','inputs':asdict(second)}]


def synthetic_csv() -> str:
    """12 invented observations, Abrams A=100/B=10, seeded 3% log noise."""
    target=io.StringIO(newline='')
    writer=csv.DictWriter(target,fieldnames=CSV_COLUMNS)
    writer.writeheader()
    rng=np.random.default_rng(15)
    for i,wc in enumerate(np.linspace(.35,.75,12)):
        cement=180/float(wc)
        fine=step7_fine(cement,3.15,180,2,1000,2.65,2.6,19,False).fine_ssd_kg_m3
        writer.writerow(dict(zip(CSV_COLUMNS,[f'SYNTHETIC-{i+1:02}','SYNTHETIC-DEMO',
            cement,180,1000,fine,'ssd',3.15,'I',2.65,1600,1,1,19,'angular',2.6,1,1,2.6,
            2,False,'moist',28,'cylinder_150x300',3,float(100/10**wc*np.exp(rng.normal(0,.03))),
            '',75,'2026-11-02','SYNTHETIC DEMO — not laboratory evidence'])))
    return target.getvalue()
