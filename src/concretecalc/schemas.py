"""Input vocabulary of the engine.

Frozen input dataclasses carry SI quantities and explicit aggregate bases.
Validation is explicit at calculation boundaries (validation.py).

The allowed values are also listed as tuples so that runtime checks can use
them with plain `in` tests (typing.Literal is not enforced at runtime).
"""

from typing import Literal
from dataclasses import dataclass

AggregateShape = Literal["angular", "subangular", "gravel_with_crushed", "round_gravel"]
AGGREGATE_SHAPES: tuple[str, ...] = ("angular", "subangular", "gravel_with_crushed", "round_gravel")

Exposure = Literal["mild", "moderate", "severe"]
EXPOSURES: tuple[str, ...] = ("mild", "moderate", "severe")

DurabilityClass = Literal["none", "low_permeability", "freeze_thaw_moist", "corrosion_protection"]
DURABILITY_CLASSES: tuple[str, ...] = ("none", "low_permeability", "freeze_thaw_moist", "corrosion_protection")

ElementType = Literal[
    "reinforced_foundation_walls_footings",
    "plain_footings_caissons_substructure_walls",
    "beams_reinforced_walls",
    "building_columns",
    "pavements_slabs",
    "mass_concrete",
]
ELEMENT_TYPES: tuple[str, ...] = (
    "reinforced_foundation_walls_footings",
    "plain_footings_caissons_substructure_walls",
    "beams_reinforced_walls",
    "building_columns",
    "pavements_slabs",
    "mass_concrete",
)

# How the mixing-water table is read along the slump axis (D-2):
#   "interpolate": linear between band midpoints 37.5 / 87.5 / 162.5 mm (task default)
#   "band"       : a slump inside a band uses that row; between bands, linear between band edges
SlumpLookup = Literal["interpolate", "band"]
SLUMP_LOOKUPS: tuple[str, ...] = ("interpolate", "band")

Curing = Literal["moist", "steam"]
CementType = Literal["I", "II", "III", "IV", "V"]
WeightBasis = Literal["oven_dry", "ssd", "as_received"]
Specimen = Literal["cylinder_150x300", "cube_150"]
MoistureConvention = Literal["course", "strict"]
DISCLAIMER = "Estimated mean strength (research prediction; NOT a certified structural design value)."


@dataclass(frozen=True)
class Binder:
    """Binder mass in kg and dimensionless specific gravity."""
    name: str
    weight_kg: float
    sg: float
    kind: Literal["cement", "scm"]


@dataclass(frozen=True)
class CoarseAggregateProperties:
    """SSD specific gravity, dry-rodded density in kg/m3; moisture in percent."""
    sg_ssd: float
    drd_kg_m3: float
    absorption_pct: float
    mc_pct: float
    shape: AggregateShape


@dataclass(frozen=True)
class FineAggregateProperties:
    """SSD specific gravity, moisture in percent, dimensionless fineness modulus."""
    sg_ssd: float
    absorption_pct: float
    mc_pct: float
    fm: float


@dataclass(frozen=True)
class Admixtures:
    """Optional product dose and water reduction; unsupported effects are flagged."""
    air_entrainer_ml_per_pct_per_100kg: float | None = None
    water_reducer_pct: float | None = None
    superplasticizer_kg: float | None = None


@dataclass(frozen=True)
class MixInputs:
    """Mode B masses in kg for the declared batch, or per m3 if volume omitted."""
    cement: Binder
    water_kg: float
    coarse_kg: float
    coarse: CoarseAggregateProperties
    fine_kg: float
    fine: FineAggregateProperties
    nmas_mm: float
    aggregate_weight_basis: WeightBasis
    air_entrained: bool
    exposure: Exposure
    cement_type: CementType = "I"
    cement_strength_class: str | None = None
    air_pct: float | None = None
    curing: Curing = "moist"
    age_days: float = 28.0
    batch_volume_m3: float | None = None
    specimen: Specimen = "cylinder_150x300"
    cube_to_cylinder_factor: float | None = None
    sigma_mpa: float | None = None
    n_samples: int | None = None
    element: ElementType | None = None
    admixtures: Admixtures = Admixtures()
    scm: tuple[Binder, ...] = ()


@dataclass(frozen=True)
class ModeAInputs:
    """Mode A design inputs: MPa, mm, kg/m3, m3 and percent."""
    specified_fc_mpa: float
    element: ElementType
    exposure: Exposure
    air_entrained: bool
    cement_sg: float
    coarse: CoarseAggregateProperties
    fine: FineAggregateProperties
    sigma_mpa: float | None = None
    n_samples: int | None = None
    slump_target_mm: float | None = None
    hand_consolidated: bool = False
    nmas_mm: float | None = None
    form_min_dimension_mm: float | None = None
    rebar_clear_spacing_mm: float | None = None
    cover_mm: float | None = None
    slab_thickness_mm: float | None = None
    durability_class: DurabilityClass = "none"
    underwater: bool = False
    flatwork: bool = False
    cement_type: CementType = "I"
    curing: Curing = "moist"
    water_reducer_pct: float | None = None
    moisture_convention: MoistureConvention = "course"
    bb0_adjustment_factor: float = 1.0
    batch_volume_m3: float = 1.0


def binders(inputs: MixInputs) -> tuple[Binder, ...]:
    """Return cement first, then supplementary binders, without changing masses."""
    return (inputs.cement,) + inputs.scm
