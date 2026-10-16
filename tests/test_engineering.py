
import pytest

from concrete_ml.features.engineering import (
    water_to_binder_ratio,
    replacement_percentage,
    compressive_strength
)


def test_water_to_binder_ratio():
    assert water_to_binder_ratio(
        water=180,
        cement=300,
        fly_ash=60,
        slag=40
    ) == pytest.approx(0.45)


def test_replacement_percentage():
    assert replacement_percentage(
        original_mass=320,
        replacement_mass=80
    ) == pytest.approx(20.0)


def test_compressive_strength():
    result = compressive_strength(
        failure_load_kn=320,
        diameter_mm=100
    )

    assert result == pytest.approx(40.74, abs=0.02)


def test_invalid_binder():
    with pytest.raises(ValueError):
        water_to_binder_ratio(180, 0)
