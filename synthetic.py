"""Synthetic data generator for ClimateShield AI.

Provides seeded, deterministic scenario simulations for demonstrations and offline drills:
- 'Cyclone-style heavy burst'
- 'Steady monsoon'
- 'Dry spell'

Always outputs ForecastData with source='synthetic'.
Never invoked silently or automatically.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import pandas as pd

from models import Location, DataQuality, ForecastData
from config import PRESET_LOCATIONS

AVAILABLE_SCENARIOS: List[str] = [
    "Cyclone-style heavy burst",
    "Steady monsoon",
    "Dry spell",
]

SCENARIO_DESCRIPTIONS: Dict[str, str] = {
    "Cyclone-style heavy burst": "Extreme convective rainfall burst (25-35 mm/h peak), mimicking cyclonic landfall conditions.",
    "Steady monsoon": "Continuous, persistent moderate rainfall (4-8 mm/h) over a multi-day active monsoon trough.",
    "Dry spell": "Sub-tropical dry period with clear skies and trace or zero precipitation.",
}


def generate_scenario(
    scenario_name: str,
    location: Optional[Location] = None,
    seed: int = 42,
    forecast_days: int = 3,
) -> ForecastData:
    """Generate a reproducible, seeded synthetic precipitation forecast.

    Always tags source='synthetic' and notes synthetic status in data quality warnings.
    """
    if scenario_name not in AVAILABLE_SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario_name}'. Expected one of {AVAILABLE_SCENARIOS}.")

    if location is None:
        location = PRESET_LOCATIONS.get("Chennai (Tamil Nadu)", Location(
            name="Chennai",
            country="India",
            admin1="Tamil Nadu",
            latitude=13.0827,
            longitude=80.2707,
            timezone="Asia/Kolkata",
        ))

    rng = random.Random(seed)
    total_hours = forecast_days * 24
    start_dt = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    times = [(start_dt + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(total_hours)]
    precip_list: List[float] = [0.0] * total_hours
    prob_list: List[float] = [0.0] * total_hours

    if scenario_name == "Cyclone-style heavy burst":
        # Landfall burst between hours 14 and 26
        burst_start = 14
        burst_end = 26
        for i in range(total_hours):
            if burst_start <= i <= burst_end:
                # Intense core
                peak_multiplier = 1.0 - abs(i - 20) / 7.0
                base_rain = 20.0 + 15.0 * max(0.1, peak_multiplier)
                noise = rng.uniform(-2.5, 3.5)
                val = max(5.0, round(base_rain + noise, 1))
                prob = min(100.0, round(90.0 + rng.uniform(0.0, 9.0), 1))
            elif (burst_start - 6) <= i < burst_start or burst_end < i <= (burst_end + 12):
                # Outer rain bands
                val = max(0.5, round(rng.uniform(2.0, 9.0), 1))
                prob = round(rng.uniform(65.0, 85.0), 1)
            else:
                # Pre/post calm
                val = max(0.0, round(rng.uniform(0.0, 0.8) if rng.random() > 0.6 else 0.0, 1))
                prob = round(rng.uniform(10.0, 30.0), 1)
            precip_list[i] = val
            prob_list[i] = prob

    elif scenario_name == "Steady monsoon":
        # Consistent moderate rainfall (1.2 to 3.2 mm/h)
        for i in range(total_hours):
            val = round(rng.uniform(1.2, 3.2), 1)
            prob = round(rng.uniform(60.0, 80.0), 1)
            precip_list[i] = val
            prob_list[i] = prob

    elif scenario_name == "Dry spell":
        # Very little to zero rain
        for i in range(total_hours):
            val = round(0.1 if rng.random() < 0.05 else 0.0, 1)
            prob = round(rng.uniform(0.0, 15.0), 1)
            precip_list[i] = val
            prob_list[i] = prob

    hourly_df = pd.DataFrame({
        "time": times,
        "precipitation": precip_list,
        "precipitation_probability": prob_list,
        "rain": precip_list,
    })

    # Build daily aggregated dataframe
    daily_rows = []
    for day_idx in range(forecast_days):
        day_slice = hourly_df.iloc[day_idx * 24 : (day_idx + 1) * 24]
        date_str = times[day_idx * 24].split("T")[0]
        daily_rows.append({
            "date": date_str,
            "precipitation_sum": round(float(day_slice["precipitation"].sum()), 1),
            "precipitation_hours": float((day_slice["precipitation"] >= 0.1).sum()),
            "precipitation_probability_max": float(day_slice["precipitation_probability"].max()),
        })
    daily_df = pd.DataFrame(daily_rows)

    quality = DataQuality(
        completeness_pct=100.0,
        missing_fields=[],
        warnings=["SYNTHETIC DEMO DATA: Generated scenario for demonstration purposes only."],
    )

    return ForecastData(
        location=location,
        source="synthetic",
        fetched_at_utc=start_dt.isoformat(),
        timezone=location.timezone,
        units={
            "precipitation": "mm",
            "precipitation_probability": "%",
            "rain": "mm",
        },
        hourly=hourly_df,
        daily=daily_df,
        past_hours=0,
        quality=quality,
    )
