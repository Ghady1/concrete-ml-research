"""Bolomey provisional research model (task section 6)."""
from concretecalc.strength import MixState, ModelConstants, StrengthPrediction, check_model_inputs, prediction


def predict_bolomey(mix: MixState, constants: ModelConstants) -> StrengthPrediction:
    """28-day MPa = K*(1/wc-0.5); no additional air term."""
    check_model_inputs(mix, constants, 'bolomey')
    return prediction('bolomey', constants.values['K'] * (1/mix.wc - .5), mix, constants)
