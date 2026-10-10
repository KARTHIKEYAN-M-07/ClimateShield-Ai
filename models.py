"""Data models and shared contracts for ClimateShield AI.

All modules interact strictly through these dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional
import pandas as pd


@dataclass(frozen=True)
class Location:
    """Geographic location specification."""

    name: str
    country: str
    admin1: str
    latitude: float
    longitude: float
    timezone: str

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Latitude {self.latitude} must be within [-90.0, 90.0].")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Longitude {self.longitude} must be within [-180.0, 180.0].")


@dataclass
class DataQuality:
    """Metadata detailing completeness and sanity of weather data."""

    completeness_pct: float
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ForecastData:
    """Standardized precipitation forecast package from Open-Meteo or synthetic generator."""

    location: Location
    source: Literal["live", "synthetic", "cached"]
    fetched_at_utc: str
    timezone: str
    units: Dict[str, str]
    hourly: pd.DataFrame
    # Expected hourly columns: ['time', 'precipitation', 'precipitation_probability', 'rain']
    daily: pd.DataFrame
    # Expected daily columns: ['date', 'precipitation_sum', 'precipitation_hours', 'precipitation_probability_max']
    past_hours: int
    quality: DataQuality


@dataclass
class RiskConfig:
    """Configuration weights and baseline thresholds for the Rainfall Risk Indicator heuristic."""

    thresholds: Dict[str, float]
    weights: Dict[str, float]


@dataclass
class RiskResult:
    """Computed Rainfall Risk Indicator results and transparent explanation."""

    score: float  # Clamped strictly 0.0 - 100.0
    category: Literal["Low", "Moderate", "High", "Severe"]
    contributions: Dict[str, float]
    drivers: List[str]
    explanation: str
    not_accounted_for: List[str]


@dataclass
class FetchError(Exception):
    """Normalized domain error for weather data fetching failures."""

    kind: Literal["timeout", "http", "rate_limit", "bad_json", "offline", "no_data"]
    message: str

    def __str__(self) -> str:
        return f"[{self.kind.upper()}] {self.message}"
