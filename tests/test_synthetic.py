"""Tests for synthetic.py scenario generator."""

import pytest
from synthetic import generate_scenario, AVAILABLE_SCENARIOS
from risk import compute_risk, find_peak_window, sensitivity


def test_seed_determinism():
    data1 = generate_scenario("Cyclone-style heavy burst", seed=100)
    data2 = generate_scenario("Cyclone-style heavy burst", seed=100)
    data_diff = generate_scenario("Cyclone-style heavy burst", seed=200)

    # Identical seed produces identical precipitation series
    assert data1.hourly["precipitation"].tolist() == data2.hourly["precipitation"].tolist()
    assert data1.hourly["precipitation_probability"].tolist() == data2.hourly["precipitation_probability"].tolist()
    assert data1.daily["precipitation_sum"].tolist() == data2.daily["precipitation_sum"].tolist()

    # Different seed produces different precipitation series
    assert data1.hourly["precipitation"].tolist() != data_diff.hourly["precipitation"].tolist()


def test_synthetic_labeling():
    for name in AVAILABLE_SCENARIOS:
        data = generate_scenario(name, seed=42)
        assert data.source == "synthetic"
        assert any("SYNTHETIC" in w for w in data.quality.warnings)


def test_unknown_scenario_raises():
    with pytest.raises(ValueError, match="Unknown scenario"):
        generate_scenario("Alien Rainstorm")


def test_all_scenarios_pass_through_risk():
    # Cyclone burst should produce High or Severe risk
    cyclone = generate_scenario("Cyclone-style heavy burst", seed=42)
    cyclone_risk = compute_risk(cyclone.hourly)
    assert cyclone_risk.category in ["High", "Severe"]
    assert cyclone_risk.score >= 50.0

    # Steady monsoon should produce Moderate or High risk
    monsoon = generate_scenario("Steady monsoon", seed=42)
    monsoon_risk = compute_risk(monsoon.hourly)
    assert monsoon_risk.category in ["Moderate", "High"]

    # Dry spell should produce Low risk
    dry = generate_scenario("Dry spell", seed=42)
    dry_risk = compute_risk(dry.hourly)
    assert dry_risk.category == "Low"
    assert dry_risk.score < 25.0


def test_synthetic_data_auxiliary_risk_tools():
    cyclone = generate_scenario("Cyclone-style heavy burst", seed=42)
    peak = find_peak_window(cyclone.hourly)
    assert peak["total_rain_mm"] > 0.0
    assert peak["peak_intensity_mm"] > 0.0

    sens = sensitivity(cyclone.hourly)
    assert sens["status"] in ["stable", "borderline"]
