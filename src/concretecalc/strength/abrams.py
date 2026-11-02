"""Abrams research model; fixed materials, placement, curing and test conditions."""
from concretecalc.strength import MixState, ModelConstants, StrengthPrediction, check_model_inputs, prediction


def predict_abrams(mix: MixState, constants: ModelConstants) -> StrengthPrediction:
    """28-day MPa = A/B**wc; separate AE presets, no extra air correction."""
    check_model_inputs(mix, constants, 'abrams')
    if constants.values['B'] <= 1:
        raise ValueError('Abrams B must exceed 1 for decreasing strength')
    value_mpa = constants.values['A'] / constants.values['B']**mix.wc
    return prediction('abrams', value_mpa, mix, constants)
