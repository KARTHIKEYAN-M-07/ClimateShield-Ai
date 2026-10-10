"""Pytest configuration and reusable fixtures for ClimateShield AI tests."""

import pytest
import pandas as pd
from datetime import datetime, timezone
from models import Location, DataQuality, ForecastData, RiskConfig, RiskResult
from config import DEFAULT_CONFIG


@pytest.fixture
def sample_location() -> Location:
    return Location(
        name="Chennai",
        country="India",
        admin1="Tamil Nadu",
        latitude=13.0827,
        longitude=80.2707,
        timezone="Asia/Kolkata",
    )


@pytest.fixture
def sample_data_quality() -> DataQuality:
    return DataQuality(
        completeness_pct=100.0,
        missing_fields=[],
        warnings=[],
    )


@pytest.fixture
def sample_hourly_df() -> pd.DataFrame:
    # 72 hours of synthetic/sample data
    times = pd.date_range("2026-10-09 00:00", periods=72, freq="h").strftime("%Y-%m-%dT%H:%M").tolist()
    # Moderate rain pattern: mostly light, one 6h burst
    precip = [0.0] * 72
    precip_prob = [10.0] * 72
    rain = [0.0] * 72
    
    # Add a burst between hour 12 and 18
    for i in range(12, 18):
        precip[i] = 15.0
        precip_prob[i] = 90.0
        rain[i] = 15.0
        
    return pd.DataFrame({
        "time": times,
        "precipitation": precip,
        "precipitation_probability": precip_prob,
        "rain": rain,
    })


@pytest.fixture
def sample_daily_df() -> pd.DataFrame:
    dates = ["2026-10-09", "2026-10-10", "2026-10-11"]
    return pd.DataFrame({
        "date": dates,
        "precipitation_sum": [90.0, 0.0, 0.0],
        "precipitation_hours": [6.0, 0.0, 0.0],
        "precipitation_probability_max": [90.0, 10.0, 10.0],
    })


@pytest.fixture
def sample_forecast_data(sample_location, sample_hourly_df, sample_daily_df, sample_data_quality) -> ForecastData:
    return ForecastData(
        location=sample_location,
        source="live",
        fetched_at_utc=datetime.now(timezone.utc).isoformat(),
        timezone="Asia/Kolkata",
        units={
            "precipitation": "mm",
            "precipitation_probability": "%",
            "rain": "mm",
        },
        hourly=sample_hourly_df,
        daily=sample_daily_df,
        past_hours=0,
        quality=sample_data_quality,
    )


@pytest.fixture
def default_risk_config() -> RiskConfig:
    return DEFAULT_CONFIG
