"""Tests for data.py Open-Meteo fetching, error handling, caching, and parsing."""

import json
import pytest
import requests
from unittest.mock import Mock, patch

from models import Location, ForecastData, FetchError
from data import (
    fetch_forecast,
    search_locations,
    get_last_cached_forecast,
    clear_caches,
    _parse_hourly_data,
)


@pytest.fixture(autouse=True)
def clean_cache_state():
    clear_caches()
    yield
    clear_caches()


@pytest.fixture
def mock_normal_payload():
    return {
        "latitude": 13.08,
        "longitude": 80.27,
        "timezone": "Asia/Kolkata",
        "hourly_units": {
            "time": "iso8601",
            "precipitation": "mm",
            "precipitation_probability": "%",
            "rain": "mm",
        },
        "daily_units": {
            "time": "iso8601",
            "precipitation_sum": "mm",
            "precipitation_hours": "h",
            "precipitation_probability_max": "%",
        },
        "hourly": {
            "time": [f"2026-10-09T{h:02d}:00" for h in range(24)],
            "precipitation": [2.5] * 24,
            "precipitation_probability": [60.0] * 24,
            "rain": [2.5] * 24,
        },
        "daily": {
            "time": ["2026-10-09"],
            "precipitation_sum": [60.0],
            "precipitation_hours": [24.0],
            "precipitation_probability_max": [60.0],
        },
    }


def test_fetch_forecast_normal(sample_location, mock_normal_payload):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_normal_payload

    with patch("requests.get", return_value=mock_resp):
        res = fetch_forecast(sample_location, forecast_days=1, past_days=0)

    assert isinstance(res, ForecastData)
    assert res.source == "live"
    assert res.units["precipitation"] == "mm"
    assert len(res.hourly) == 24
    assert res.quality.completeness_pct == 100.0
    assert len(res.quality.warnings) == 0


def test_fetch_forecast_dynamic_units(sample_location, mock_normal_payload):
    mock_normal_payload["hourly_units"]["precipitation"] = "inch"
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_normal_payload

    with patch("requests.get", return_value=mock_resp):
        res = fetch_forecast(sample_location, forecast_days=1, past_days=0)

    assert res.units["precipitation"] == "inch"


def test_fetch_forecast_nulls_handling(sample_location, mock_normal_payload):
    # Insert nulls into precipitation
    mock_normal_payload["hourly"]["precipitation"][0] = None
    mock_normal_payload["hourly"]["rain"][1] = None
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_normal_payload

    with patch("requests.get", return_value=mock_resp):
        res = fetch_forecast(sample_location, forecast_days=1, past_days=0)

    assert res.quality.completeness_pct < 100.0
    # Nulls should be cleanly converted to 0.0
    assert res.hourly.iloc[0]["precipitation"] == 0.0
    assert res.hourly.iloc[1]["rain"] == 0.0


def test_fetch_forecast_mismatched_lengths(sample_location, mock_normal_payload):
    # Shorten rain array
    mock_normal_payload["hourly"]["rain"] = [1.0, 2.0]
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_normal_payload

    with patch("requests.get", return_value=mock_resp):
        res = fetch_forecast(sample_location, forecast_days=1, past_days=0)

    assert len(res.hourly) == 24
    assert any("Mismatched length" in w for w in res.quality.warnings)


def test_fetch_forecast_empty_hourly(sample_location, mock_normal_payload):
    mock_normal_payload["hourly"]["time"] = []
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_normal_payload

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(FetchError) as exc_info:
            fetch_forecast(sample_location, forecast_days=1, past_days=0)

    assert exc_info.value.kind == "no_data"


def test_fetch_forecast_timeout_retry_and_failure(sample_location):
    with patch("requests.get", side_effect=requests.exceptions.Timeout("Timeout")):
        with pytest.raises(FetchError) as exc_info:
            fetch_forecast(sample_location, max_retries=2, backoff_factor=0.01)

    assert exc_info.value.kind == "timeout"


def test_fetch_forecast_500_server_error(sample_location):
    mock_resp = Mock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(FetchError) as exc_info:
            fetch_forecast(sample_location, max_retries=2, backoff_factor=0.01)

    assert exc_info.value.kind == "http"


def test_fetch_forecast_429_rate_limit(sample_location):
    mock_resp = Mock()
    mock_resp.status_code = 429

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(FetchError) as exc_info:
            fetch_forecast(sample_location, max_retries=2, backoff_factor=0.01)

    assert exc_info.value.kind == "rate_limit"


def test_fetch_forecast_invalid_json(sample_location):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(FetchError) as exc_info:
            fetch_forecast(sample_location, max_retries=1)

    assert exc_info.value.kind == "bad_json"


def test_fetch_forecast_offline(sample_location):
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("No connection")):
        with pytest.raises(FetchError) as exc_info:
            fetch_forecast(sample_location, max_retries=1, backoff_factor=0.01)

    assert exc_info.value.kind == "offline"


def test_fetch_forecast_bad_days_range(sample_location):
    with pytest.raises(FetchError) as exc_info:
        fetch_forecast(sample_location, forecast_days=10)
    assert exc_info.value.kind == "bad_json"

    with pytest.raises(FetchError) as exc_info:
        fetch_forecast(sample_location, past_days=5)
    assert exc_info.value.kind == "bad_json"


def test_fallback_cache_after_failure(sample_location, mock_normal_payload):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_normal_payload

    # First successful fetch
    with patch("requests.get", return_value=mock_resp):
        res1 = fetch_forecast(sample_location, forecast_days=1, past_days=0)
    assert res1.source == "live"

    # Subsequent fetch fails with offline
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Network down")):
        with pytest.raises(FetchError):
            # Use different days param so it bypasses TTL cache and attempts network
            fetch_forecast(sample_location, forecast_days=2, past_days=0, max_retries=1, backoff_factor=0.01)

    # Check fallback cache is available
    cached_fallback = get_last_cached_forecast(sample_location.latitude, sample_location.longitude)
    assert cached_fallback is not None
    assert cached_fallback.source == "cached"
    assert cached_fallback.location.name == "Chennai"


def test_search_locations_success():
    payload = {
        "results": [
            {
                "name": "Madurai",
                "country": "India",
                "admin1": "Tamil Nadu",
                "latitude": 9.9252,
                "longitude": 78.1198,
                "timezone": "Asia/Kolkata",
            }
        ]
    }
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = payload

    with patch("requests.get", return_value=mock_resp):
        locs = search_locations("Madurai")

    assert len(locs) == 1
    assert locs[0].name == "Madurai"
    assert locs[0].latitude == 9.9252


def test_search_locations_empty_and_errors():
    # Empty query
    assert search_locations("   ") == []

    # 429 rate limit
    mock_429 = Mock(status_code=429)
    with patch("requests.get", return_value=mock_429):
        with pytest.raises(FetchError) as exc_info:
            search_locations("Chennai")
        assert exc_info.value.kind == "rate_limit"

    # Offline
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Offline")):
        with pytest.raises(FetchError) as exc_info:
            search_locations("Chennai")
        assert exc_info.value.kind == "offline"
