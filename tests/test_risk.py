"""Tests for risk.py heuristic calculation engine."""

import pytest
import pandas as pd
from models import RiskConfig
from config import DEFAULT_CONFIG
from risk import (
    compute_risk,
    calculate_factors,
    find_peak_window,
    sensitivity,
    apply_scenario,
    _calculate_consecutive_wet_hours,
)


def create_hourly(precip_vals, prob_vals=None):
    n = len(precip_vals)
    times = [f"2026-10-09T{h:02d}:00" for h in range(n)]
    probs = prob_vals if prob_vals is not None else [50.0] * n
    return pd.DataFrame({
        "time": times,
        "precipitation": precip_vals,
        "precipitation_probability": probs,
        "rain": precip_vals,
    })


def test_all_zero_rain():
    hourly = create_hourly([0.0] * 72, [0.0] * 72)
    res = compute_risk(hourly)
    assert res.score == 0.0
    assert res.category == "Low"
    assert all(c == 0.0 for c in res.contributions.values())
    assert len(res.drivers) > 0


def test_extreme_rain_clamping():
    # Massive flood-level rain (100mm every hour for 72h)
    hourly = create_hourly([100.0] * 72, [100.0] * 72)
    res = compute_risk(hourly)
    assert res.score == 100.0
    assert res.category == "Severe"
    assert len(res.drivers) == 3


def test_monotonicity():
    hourly_light = create_hourly([1.0] * 72, [20.0] * 72)
    hourly_moderate = create_hourly([5.0] * 72, [60.0] * 72)
    hourly_heavy = create_hourly([20.0] * 72, [90.0] * 72)

    res_light = compute_risk(hourly_light)
    res_mod = compute_risk(hourly_moderate)
    res_heavy = compute_risk(hourly_heavy)

    assert res_light.score < res_mod.score < res_heavy.score


def test_determinism(sample_hourly_df):
    first_res = compute_risk(sample_hourly_df)
    for _ in range(5):
        subsequent = compute_risk(sample_hourly_df)
        assert subsequent.score == first_res.score
        assert subsequent.category == first_res.category
        assert subsequent.contributions == first_res.contributions


def test_weight_changes(sample_hourly_df):
    custom_cfg = RiskConfig(
        thresholds=DEFAULT_CONFIG.thresholds,
        weights={
            "weight_24h": 1.0,
            "weight_72h": 0.0,
            "weight_peak_intensity": 0.0,
            "weight_peak_prob": 0.0,
            "weight_consecutive": 0.0,
            "weight_recent": 0.0,
        },
    )
    res = compute_risk(sample_hourly_df, config=custom_cfg)
    assert res.contributions["rain_72h"] == 0.0
    assert res.contributions["peak_intensity"] == 0.0
    assert res.contributions["rain_24h"] > 0.0


def test_consecutive_wet_hours():
    # 0, 1.5, 2.0, 3.0, 0.5, 2.0, 2.0, 0
    s = pd.Series([0.0, 1.5, 2.0, 3.0, 0.5, 2.0, 2.0, 0.0])
    # Run of length 3 (1.5, 2.0, 3.0) and run of length 2 (2.0, 2.0)
    assert _calculate_consecutive_wet_hours(s, wet_threshold=1.0) == 3.0


def test_find_peak_window():
    # 12 hours: hours 4-9 have high rain
    precips = [0.0, 0.0, 0.0, 0.0, 10.0, 20.0, 30.0, 15.0, 5.0, 0.0, 0.0, 0.0]
    hourly = create_hourly(precips)
    peak = find_peak_window(hourly)

    assert peak["total_rain_mm"] == 80.0
    assert peak["peak_intensity_mm"] == 30.0
    assert peak["start_time"] == "2026-10-09T03:00"
    assert peak["end_time"] == "2026-10-09T08:00"


def test_find_peak_window_empty_and_short():
    empty_res = find_peak_window(pd.DataFrame())
    assert empty_res["total_rain_mm"] == 0.0

    short_hourly = create_hourly([5.0, 10.0, 2.0])
    short_res = find_peak_window(short_hourly)
    assert short_res["total_rain_mm"] == 17.0
    assert short_res["peak_intensity_mm"] == 10.0


def test_sensitivity_classification(sample_hourly_df):
    sens = sensitivity(sample_hourly_df)
    assert sens["status"] in ["stable", "borderline"]
    assert sens["min_score"] <= sens["base_score"] <= sens["max_score"]
    assert sens["range"] >= 0.0


def test_apply_scenario(sample_hourly_df):
    base_precip = sample_hourly_df["precipitation"].sum()
    scaled_1_5 = apply_scenario(sample_hourly_df, 1.5)
    new_precip = scaled_1_5["precipitation"].sum()

    assert round(new_precip, 1) == round(base_precip * 1.5, 1)
    assert scaled_1_5["precipitation_probability"].max() <= 100.0


def test_missing_or_empty_dataframe():
    empty_df = pd.DataFrame()
    res = compute_risk(empty_df)
    assert res.score == 0.0
    assert res.category == "Low"
