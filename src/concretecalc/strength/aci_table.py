"""Invert the required-average-strength table, retaining interpolation status."""
from concretecalc.strength import MixState, ModelConstants, StrengthPrediction, check_model_inputs, prediction
from concretecalc.tables.lookups import strength_for_wc
from concretecalc.tables.interpolate import Policy


def predict_aci_table(mix: MixState, constants: ModelConstants,
                      policy: Policy = 'extrapolate') -> StrengthPrediction:
    """28-day mean MPa from w/c, using AE or non-AE required-mean table."""
    check_model_inputs(mix, constants, 'aci_table')
    lookup = strength_for_wc(mix.wc, mix.air_entrained, policy)
    return prediction('aci_table', lookup.value, mix, constants, lookup.status, lookup.warnings)
