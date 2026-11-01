"""Input vocabulary of the engine.

M4 adds only the Literal type aliases that the table lookups need. The input
dataclasses (Binder, MixInputs, ModeAInputs, ...) and DISCLAIMER are added in M5.

The allowed values are also listed as tuples so that runtime checks can use
them with plain `in` tests (typing.Literal is not enforced at runtime).
"""

from typing import Literal

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
