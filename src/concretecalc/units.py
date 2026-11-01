"""Unit conversions used ONLY at boundaries (UI adapters, US-unit inputs, psi table values).

Everything inside the engine is SI (CLAUDE.md ground rule 2). The factors are
exact definitions from task section 8 (ASSUMPTIONS A-04: they are definitions,
not empirical reference data, so they live here and not in a JSON table).
"""

KG_PER_LB = 0.45359237                       # 1 lb = 0.45359237 kg (exact)
MM_PER_IN = 25.4                             # 1 in = 25.4 mm (exact)
M_PER_YD = 0.9144                            # 1 yd = 0.9144 m (exact)
MPA_PER_PSI = 0.00689475729                  # 1 psi = 0.00689475729 MPa (task section 8)
KG_M3_PER_PCF = 16.01846337                  # 1 lb/ft3 = 16.01846337 kg/m3 (task section 8)
M3_PER_YD3 = 0.764554857984                  # 1 yd3 = 0.9144**3 m3 (exact)
KG_M3_PER_LB_YD3 = KG_PER_LB / M3_PER_YD3    # 1 lb/yd3 ~ 0.593276 kg/m3


def lb_to_kg(mass_lb: float) -> float:
    """Mass: pounds -> kilograms."""
    return mass_lb * KG_PER_LB


def kg_to_lb(mass_kg: float) -> float:
    """Mass: kilograms -> pounds."""
    return mass_kg / KG_PER_LB


def in_to_mm(length_in: float) -> float:
    """Length: inches -> millimetres."""
    return length_in * MM_PER_IN


def mm_to_in(length_mm: float) -> float:
    """Length: millimetres -> inches."""
    return length_mm / MM_PER_IN


def psi_to_mpa(stress_psi: float) -> float:
    """Stress: psi -> MPa."""
    return stress_psi * MPA_PER_PSI


def mpa_to_psi(stress_mpa: float) -> float:
    """Stress: MPa -> psi."""
    return stress_mpa / MPA_PER_PSI


def pcf_to_kg_m3(density_pcf: float) -> float:
    """Density: lb/ft3 (pcf) -> kg/m3."""
    return density_pcf * KG_M3_PER_PCF


def kg_m3_to_pcf(density_kg_m3: float) -> float:
    """Density: kg/m3 -> lb/ft3 (pcf)."""
    return density_kg_m3 / KG_M3_PER_PCF


def lb_yd3_to_kg_m3(content_lb_yd3: float) -> float:
    """Mix content: lb per cubic yard -> kg per cubic metre."""
    return content_lb_yd3 * KG_M3_PER_LB_YD3


def kg_m3_to_lb_yd3(content_kg_m3: float) -> float:
    """Mix content: kg per cubic metre -> lb per cubic yard."""
    return content_kg_m3 / KG_M3_PER_LB_YD3


def yd3_to_m3(volume_yd3: float) -> float:
    """Volume: cubic yards -> cubic metres."""
    return volume_yd3 * M3_PER_YD3


def m3_to_yd3(volume_m3: float) -> float:
    """Volume: cubic metres -> cubic yards."""
    return volume_m3 / M3_PER_YD3
