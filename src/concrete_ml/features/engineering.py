
import math


def water_to_binder_ratio(
    water: float,
    cement: float,
    fly_ash: float = 0,
    slag: float = 0
) -> float:
    """Calculate water-to-binder mass ratio."""

    materials = [water, cement, fly_ash, slag]

    if any(x < 0 for x in materials):
        raise ValueError("Negative material quantities are invalid.")

    binder = cement + fly_ash + slag

    if binder <= 0:
        raise ValueError("Total binder must be positive.")

    return water / binder


def replacement_percentage(
    original_mass: float,
    replacement_mass: float
) -> float:
    """Calculate mass-based replacement percentage."""

    if original_mass < 0 or replacement_mass < 0:
        raise ValueError("Masses cannot be negative.")

    total = original_mass + replacement_mass

    if total <= 0:
        raise ValueError("Total mass must be positive.")

    return 100 * replacement_mass / total


def compressive_strength(
    failure_load_kn: float,
    diameter_mm: float
) -> float:
    """Calculate cylindrical specimen strength in MPa."""

    if failure_load_kn <= 0 or diameter_mm <= 0:
        raise ValueError("Load and diameter must be positive.")

    area_mm2 = math.pi * diameter_mm**2 / 4

    return failure_load_kn * 1000 / area_mm2
