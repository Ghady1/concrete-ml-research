"""Common model registry and provisional presets, PLAN M09."""
from dataclasses import replace

from concretecalc.strength import MixState, ModelConstants, StrengthModel
from concretecalc.strength.aci_table import predict_aci_table
from concretecalc.strength.abrams import predict_abrams
from concretecalc.strength.bolomey import predict_bolomey
from concretecalc.strength.feret import predict_feret
from concretecalc.tables.lookups import model_presets

MODEL_REGISTRY: dict[str, StrengthModel] = {
    'aci_table': predict_aci_table, 'abrams': predict_abrams,
    'bolomey': predict_bolomey, 'feret': predict_feret,
}


def default_constants(model_name: str, air_entrained: bool,
                      preset: str = 'project_fit') -> ModelConstants:
    """Return a fresh, uncalibrated named preset with source and age basis."""
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f'Unknown model_name {model_name}')
    for entry in model_presets():
        if (entry['model'] == model_name and entry['preset'] == preset
                and entry['air_entrained'] in (None, air_entrained)):
            return ModelConstants(model_name, preset, dict(entry['values']), entry['source'],
                False, entry['air_entrained'], entry['age_basis_days'])
    raise ValueError(f'Unknown preset {preset} for {model_name}, air_entrained={air_entrained}')


def list_presets(model_name: str) -> tuple[str, ...]:
    """List available preset labels, retaining their JSON order."""
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f'Unknown model_name {model_name}')
    names: list[str] = []
    for entry in model_presets():
        if entry['model'] == model_name and entry['preset'] not in names:
            names.append(entry['preset'])
    return tuple(names)


def strength_curve_mpa(model_name: str, wc_values: tuple[float, ...], reference: MixState,
                       constants: ModelConstants) -> tuple[float | None, ...]:
    """Vary cement at fixed water, SG and air; return 28-day MPa per w/c."""
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f'Unknown model_name {model_name}')
    values: list[float | None] = []
    for wc in wc_values:
        if wc <= 0:
            raise ValueError('wc_values must be positive')
        factor = reference.wc / wc
        cement_kg_m3 = reference.cement_kg_m3 * factor
        binder_kg_m3 = reference.binder_kg_m3 - reference.cement_kg_m3 + cement_kg_m3
        mix = replace(reference, wc=wc, cement_kg_m3=cement_kg_m3,
            binder_kg_m3=binder_kg_m3, wcm=reference.effective_water_kg_m3/binder_kg_m3,
            cement_volume_m3=reference.cement_volume_m3*factor)
        values.append(MODEL_REGISTRY[model_name](mix, constants).mean_28d_mpa)
    return tuple(values)
