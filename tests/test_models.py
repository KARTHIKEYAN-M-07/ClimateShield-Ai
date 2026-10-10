"""Tests for models.py data contracts."""

import pytest
import pandas as pd
from models import Location, DataQuality, ForecastData, RiskConfig, RiskResult, FetchError


def test_location_valid():
    loc = Location("Chennai", "India", "Tamil Nadu", 13.0827, 80.2707, "Asia/Kolkata")
    assert loc.name == "Chennai"
    assert loc.latitude == 13.0827
    assert loc.longitude == 80.2707


def test_location_invalid_latitude():
    with pytest.raises(ValueError, match="Latitude"):
        Location("Bad", "India", "TN", 95.0, 80.0, "Asia/Kolkata")


def test_location_invalid_longitude():
    with pytest.raises(ValueError, match="Longitude"):
        Location("Bad", "India", "TN", 13.0, 185.0, "Asia/Kolkata")


def test_data_quality():
    dq = DataQuality(completeness_pct=95.5, missing_fields=["rain"], warnings=["Imputed 1 hour"])
    assert dq.completeness_pct == 95.5
    assert "rain" in dq.missing_fields
    assert len(dq.warnings) == 1


def test_forecast_data_structure(sample_location, sample_hourly_df, sample_daily_df, sample_data_quality):
    fd = ForecastData(
        location=sample_location,
        source="live",
        fetched_at_utc="2026-10-09T12:00:00Z",
        timezone="Asia/Kolkata",
        units={"precipitation": "mm"},
        hourly=sample_hourly_df,
        daily=sample_daily_df,
        past_hours=0,
        quality=sample_data_quality,
    )
    assert fd.source == "live"
    assert len(fd.hourly) == 72
    assert len(fd.daily) == 3


def test_fetch_error_attributes():
    err = FetchError(kind="rate_limit", message="HTTP 429 Too Many Requests")
    assert err.kind == "rate_limit"
    assert "429" in str(err)
    assert isinstance(err, Exception)


def test_risk_result_contract():
    res = RiskResult(
        score=65.0,
        category="High",
        contributions={"24h": 25.0, "72h": 15.0, "intensity": 15.0, "prob": 10.0},
        drivers=["Heavy 24h accumulation (80mm)", "Sustained intensity"],
        explanation="High rainfall risk driven by heavy 24h burst.",
        not_accounted_for=["Drainage capacity", "Soil saturation"],
    )
    assert res.score == 65.0
    assert res.category == "High"
    assert len(res.drivers) == 2
    assert len(res.not_accounted_for) == 2
