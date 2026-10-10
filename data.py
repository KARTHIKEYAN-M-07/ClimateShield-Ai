"""Data layer for ClimateShield AI: Open-Meteo Geocoding and Forecast API clients.

Handles network requests, exponential-backoff retries, defensive parsing,
data quality calculation, in-memory TTL caching, and graceful cached fallback.
All failures produce FetchError, never raw exceptions.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import requests

from models import Location, DataQuality, ForecastData, FetchError

# Endpoints
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

# In-memory storage for TTL caching and fallback
# TTL cache: key -> (timestamp, ForecastData)
_TTL_CACHE: Dict[Tuple[float, float, int, int], Tuple[float, ForecastData]] = {}
TTL_SECONDS = 300.0  # 5 minutes

# Last good response per rounded coordinate: key -> ForecastData
_LAST_GOOD_CACHE: Dict[Tuple[float, float], ForecastData] = {}


def clear_caches() -> None:
    """Clear memory caches (useful for testing)."""
    _TTL_CACHE.clear()
    _LAST_GOOD_CACHE.clear()


def get_last_cached_forecast(latitude: float, longitude: float) -> Optional[ForecastData]:
    """Retrieve the last successful live response for this location marked as cached."""
    key = (round(latitude, 4), round(longitude, 4))
    cached = _LAST_GOOD_CACHE.get(key)
    if cached is not None:
        # Return a copy marked with source='cached'
        return ForecastData(
            location=cached.location,
            source="cached",
            fetched_at_utc=cached.fetched_at_utc,
            timezone=cached.timezone,
            units=cached.units,
            hourly=cached.hourly.copy(),
            daily=cached.daily.copy(),
            past_hours=cached.past_hours,
            quality=cached.quality,
        )
    return None


def search_locations(query: str, count: int = 5, timeout: int = 8) -> List[Location]:
    """Search locations by name using Open-Meteo Geocoding API.

    Returns a list of Location objects or raises FetchError on network/parsing failure.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    params = {
        "name": cleaned_query,
        "count": count,
        "language": "en",
        "format": "json",
    }

    try:
        response = requests.get(GEOCODING_API_URL, params=params, timeout=timeout)
    except requests.exceptions.Timeout as exc:
        raise FetchError("timeout", f"Geocoding request timed out: {exc}") from exc
    except requests.exceptions.ConnectionError as exc:
        raise FetchError("offline", f"Network offline or geocoding server unreachable: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise FetchError("http", f"Geocoding request failed: {exc}") from exc

    if response.status_code == 429:
        raise FetchError("rate_limit", "Open-Meteo geocoding rate limit exceeded (HTTP 429).")
    if response.status_code >= 400:
        raise FetchError("http", f"Geocoding server error: HTTP {response.status_code}.")

    try:
        data = response.json()
    except Exception as exc:
        raise FetchError("bad_json", f"Failed to parse geocoding JSON response: {exc}") from exc

    if not isinstance(data, dict):
        raise FetchError("bad_json", "Geocoding response is not a valid JSON dictionary.")

    results = data.get("results")
    if not results or not isinstance(results, list):
        return []

    locations: List[Location] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        try:
            name = str(item.get("name", "Unknown"))
            country = str(item.get("country", "Unknown"))
            admin1 = str(item.get("admin1", item.get("country", "Unknown")))
            lat = float(item["latitude"])
            lon = float(item["longitude"])
            tz = str(item.get("timezone", "UTC"))
            locations.append(Location(
                name=name,
                country=country,
                admin1=admin1,
                latitude=lat,
                longitude=lon,
                timezone=tz,
            ))
        except (KeyError, ValueError, TypeError):
            # Skip malformed items
            continue

    return locations


def _parse_hourly_data(hourly_raw: Any, units: Dict[str, str]) -> Tuple[pd.DataFrame, DataQuality]:
    """Defensively parses hourly weather dictionary into a DataFrame and DataQuality."""
    warnings: List[str] = []
    missing_fields: List[str] = []

    if not isinstance(hourly_raw, dict):
        warnings.append("Hourly payload missing or malformed; empty frame generated.")
        empty_df = pd.DataFrame(columns=["time", "precipitation", "precipitation_probability", "rain"])
        return empty_df, DataQuality(completeness_pct=0.0, missing_fields=["all"], warnings=warnings)

    required_fields = ["time", "precipitation", "precipitation_probability", "rain"]
    for field in required_fields:
        if field not in hourly_raw or not isinstance(hourly_raw[field], list):
            missing_fields.append(field)

    time_series = hourly_raw.get("time", [])
    if not isinstance(time_series, list) or len(time_series) == 0:
        warnings.append("No hourly time steps found in response.")
        empty_df = pd.DataFrame(columns=required_fields)
        return empty_df, DataQuality(completeness_pct=0.0, missing_fields=missing_fields, warnings=warnings)

    target_length = len(time_series)
    columns_data: Dict[str, List[Any]] = {"time": time_series}
    null_count = 0
    total_elements = target_length * (len(required_fields) - 1)  # numeric columns

    for field in ["precipitation", "precipitation_probability", "rain"]:
        series = hourly_raw.get(field, [])
        if not isinstance(series, list):
            series = [0.0] * target_length
            warnings.append(f"Missing field '{field}'; imputed with 0.0.")
            null_count += target_length
        elif len(series) != target_length:
            warnings.append(f"Mismatched length for '{field}' ({len(series)} vs expected {target_length}).")
            if len(series) < target_length:
                null_count += (target_length - len(series))
                series = list(series) + [0.0] * (target_length - len(series))
            else:
                series = series[:target_length]
        
        # Clean null values
        cleaned_series = []
        for val in series:
            if val is None or pd.isna(val):
                cleaned_series.append(0.0)
                null_count += 1
            else:
                try:
                    cleaned_series.append(float(val))
                except (ValueError, TypeError):
                    cleaned_series.append(0.0)
                    null_count += 1
        columns_data[field] = cleaned_series

    completeness_pct = 100.0 if total_elements == 0 else max(
        0.0, min(100.0, ((total_elements - null_count) / total_elements) * 100.0)
    )

    df = pd.DataFrame(columns_data)
    quality = DataQuality(
        completeness_pct=round(completeness_pct, 1),
        missing_fields=missing_fields,
        warnings=warnings,
    )
    return df, quality


def _parse_daily_data(daily_raw: Any) -> pd.DataFrame:
    """Defensively parses daily weather dictionary into a DataFrame."""
    required_fields = ["date", "precipitation_sum", "precipitation_hours", "precipitation_probability_max"]
    if not isinstance(daily_raw, dict):
        return pd.DataFrame(columns=required_fields)

    dates = daily_raw.get("time", [])
    if not isinstance(dates, list) or len(dates) == 0:
        return pd.DataFrame(columns=required_fields)

    target_length = len(dates)
    columns_data: Dict[str, List[Any]] = {"date": dates}

    mappings = {
        "precipitation_sum": "precipitation_sum",
        "precipitation_hours": "precipitation_hours",
        "precipitation_probability_max": "precipitation_probability_max",
    }

    for target_col, raw_key in mappings.items():
        series = daily_raw.get(raw_key, [])
        if not isinstance(series, list) or len(series) != target_length:
            series = [0.0] * target_length
        else:
            cleaned = []
            for v in series:
                try:
                    cleaned.append(float(v) if v is not None and not pd.isna(v) else 0.0)
                except (ValueError, TypeError):
                    cleaned.append(0.0)
            series = cleaned
        columns_data[target_col] = series

    return pd.DataFrame(columns_data)


def fetch_forecast(
    location: Location,
    forecast_days: int = 3,
    past_days: int = 1,
    timeout: int = 10,
    max_retries: int = 3,
    backoff_factor: float = 0.2,
    session: Optional[requests.Session] = None,
) -> ForecastData:
    """Fetch precipitation forecast from Open-Meteo Forecast API with retries and caching.

    Raises FetchError on failure. If a failure occurs, the caller may check
    `get_last_cached_forecast` for a fallback.
    """
    if not (1 <= forecast_days <= 7):
        raise FetchError("bad_json", f"forecast_days must be between 1 and 7, got {forecast_days}")
    if not (0 <= past_days <= 3):
        raise FetchError("bad_json", f"past_days must be between 0 and 3, got {past_days}")

    cache_key = (round(location.latitude, 4), round(location.longitude, 4), forecast_days, past_days)
    now_ts = time.time()

    # Check valid TTL cache
    if cache_key in _TTL_CACHE:
        cached_ts, cached_data = _TTL_CACHE[cache_key]
        if now_ts - cached_ts < TTL_SECONDS:
            return ForecastData(
                location=cached_data.location,
                source="cached",
                fetched_at_utc=cached_data.fetched_at_utc,
                timezone=cached_data.timezone,
                units=cached_data.units,
                hourly=cached_data.hourly.copy(),
                daily=cached_data.daily.copy(),
                past_hours=cached_data.past_hours,
                quality=cached_data.quality,
            )

    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "hourly": "precipitation,precipitation_probability,rain",
        "daily": "precipitation_sum,precipitation_hours,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": forecast_days,
        "past_days": past_days,
    }

    req_client = session if session is not None else requests
    last_error: Optional[FetchError] = None

    for attempt in range(max_retries):
        try:
            resp = req_client.get(FORECAST_API_URL, params=params, timeout=timeout)
        except requests.exceptions.Timeout as exc:
            last_error = FetchError("timeout", f"Connection to Open-Meteo timed out: {exc}")
            time.sleep(backoff_factor * (2 ** attempt))
            continue
        except requests.exceptions.ConnectionError as exc:
            last_error = FetchError("offline", f"Open-Meteo service unreachable or network offline: {exc}")
            time.sleep(backoff_factor * (2 ** attempt))
            continue
        except requests.exceptions.RequestException as exc:
            last_error = FetchError("http", f"HTTP request failed: {exc}")
            time.sleep(backoff_factor * (2 ** attempt))
            continue

        if resp.status_code == 429:
            last_error = FetchError("rate_limit", "Open-Meteo API rate limit exceeded (HTTP 429).")
            time.sleep(backoff_factor * (2 ** attempt))
            continue
        elif resp.status_code >= 500:
            last_error = FetchError("http", f"Open-Meteo server error: HTTP {resp.status_code}.")
            time.sleep(backoff_factor * (2 ** attempt))
            continue
        elif resp.status_code >= 400:
            raise FetchError("http", f"Open-Meteo client error: HTTP {resp.status_code} ({resp.text[:120]}).")

        # HTTP 200 OK
        try:
            payload = resp.json()
        except Exception as exc:
            raise FetchError("bad_json", f"Invalid JSON received from forecast API: {exc}") from exc

        if not isinstance(payload, dict):
            raise FetchError("bad_json", "Forecast response root is not a dictionary.")

        if "error" in payload and payload["error"]:
            reason = payload.get("reason", "Unknown API error")
            raise FetchError("bad_json", f"Open-Meteo returned error: {reason}")

        # Read units dynamically from response
        hourly_units = payload.get("hourly_units", {})
        daily_units = payload.get("daily_units", {})
        units: Dict[str, str] = {}
        if isinstance(hourly_units, dict):
            for k, v in hourly_units.items():
                units[str(k)] = str(v)
        if isinstance(daily_units, dict):
            for k, v in daily_units.items():
                units[str(k)] = str(v)
        if "precipitation" not in units:
            units["precipitation"] = "mm"

        # Defensive parsing
        hourly_df, quality = _parse_hourly_data(payload.get("hourly"), units)
        daily_df = _parse_daily_data(payload.get("daily"))

        if hourly_df.empty:
            raise FetchError("no_data", "Forecast returned empty hourly precipitation dataset.")

        tz_str = str(payload.get("timezone", location.timezone or "UTC"))
        past_hours = past_days * 24

        forecast = ForecastData(
            location=location,
            source="live",
            fetched_at_utc=datetime.now(timezone.utc).isoformat(),
            timezone=tz_str,
            units=units,
            hourly=hourly_df,
            daily=daily_df,
            past_hours=past_hours,
            quality=quality,
        )

        # Update caches
        _TTL_CACHE[cache_key] = (now_ts, forecast)
        loc_coord_key = (round(location.latitude, 4), round(location.longitude, 4))
        _LAST_GOOD_CACHE[loc_coord_key] = forecast

        return forecast

    # If all retries exhausted
    assert last_error is not None
    raise last_error
