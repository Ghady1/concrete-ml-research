"""Feret air-aware provisional model (task section 6)."""
from concretecalc.strength import MixState, ModelConstants, StrengthPrediction, check_model_inputs, prediction
from concretecalc.validation import _number


def predict_feret(mix: MixState, constants: ModelConstants) -> StrengthPrediction:
    """28-day MPa=K*(Vc/(Vc+Vw+Va))**2 with per-m3 absolute volumes."""
    check_model_inputs(mix, constants, 'feret')
    _number(mix.cement_volume_m3, 'cement_volume_m3', strict=True)
    _number(mix.water_volume_m3, 'water_volume_m3', strict=True)
    _number(mix.air_volume_m3, 'air_volume_m3')
    ratio = mix.cement_volume_m3 / (mix.cement_volume_m3 + mix.water_volume_m3 + mix.air_volume_m3)
    return prediction('feret', constants.values['K'] * ratio**2, mix, constants)
