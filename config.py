"""Configuration, constants, presets, and defaults for ClimateShield AI."""

from typing import Dict, List
from models import Location, RiskConfig

# Single authoritative default risk configuration
DEFAULT_CONFIG = RiskConfig(
    thresholds={
        "rain_24h_high": 70.0,            # mm (IMD heavy rain definition > 64.5 mm)
        "rain_72h_high": 150.0,           # mm (3-day cumulative heavy spell)
        "peak_intensity_high": 20.0,       # mm/h (intense cloudburst or convective cell)
        "peak_prob_high": 85.0,            # % probability
        "consecutive_wet_hours_high": 10.0,# continuous rain >= 1mm/h
        "recent_rain_high": 40.0,          # mm in past 24-48h context
    },
    weights={
        "weight_24h": 0.30,
        "weight_72h": 0.20,
        "weight_peak_intensity": 0.20,
        "weight_peak_prob": 0.10,
        "weight_consecutive": 0.10,
        "weight_recent": 0.10,
    },
)

# Risk Category Bands
RISK_CATEGORIES = {
    "Low": {"min": 0.0, "max": 25.0, "color": "#22c55e", "badge": "🟢 Low"},
    "Moderate": {"min": 25.0, "max": 50.0, "color": "#eab308", "badge": "🟡 Moderate"},
    "High": {"min": 50.0, "max": 75.0, "color": "#f97316", "badge": "🟠 High"},
    "Severe": {"min": 75.0, "max": 100.0, "color": "#ef4444", "badge": "🔴 Severe"},
}

# Presets: Tamil Nadu districts (priority) + International cities
PRESET_LOCATIONS: Dict[str, Location] = {
    "Chennai (Tamil Nadu)": Location(
        name="Chennai",
        country="India",
        admin1="Tamil Nadu",
        latitude=13.0827,
        longitude=80.2707,
        timezone="Asia/Kolkata",
    ),
    "Cuddalore (Tamil Nadu)": Location(
        name="Cuddalore",
        country="India",
        admin1="Tamil Nadu",
        latitude=11.7480,
        longitude=79.7714,
        timezone="Asia/Kolkata",
    ),
    "Nagapattinam (Tamil Nadu)": Location(
        name="Nagapattinam",
        country="India",
        admin1="Tamil Nadu",
        latitude=10.7656,
        longitude=79.8424,
        timezone="Asia/Kolkata",
    ),
    "Madurai (Tamil Nadu)": Location(
        name="Madurai",
        country="India",
        admin1="Tamil Nadu",
        latitude=9.9252,
        longitude=78.1198,
        timezone="Asia/Kolkata",
    ),
    "Coimbatore (Tamil Nadu)": Location(
        name="Coimbatore",
        country="India",
        admin1="Tamil Nadu",
        latitude=11.0168,
        longitude=76.9558,
        timezone="Asia/Kolkata",
    ),
    "Tiruchirappalli (Tamil Nadu)": Location(
        name="Tiruchirappalli",
        country="India",
        admin1="Tamil Nadu",
        latitude=10.7905,
        longitude=78.7047,
        timezone="Asia/Kolkata",
    ),
    "Erode (Tamil Nadu)": Location(
        name="Erode",
        country="India",
        admin1="Tamil Nadu",
        latitude=11.3410,
        longitude=77.7172,
        timezone="Asia/Kolkata",
    ),
    "London (UK)": Location(
        name="London",
        country="United Kingdom",
        admin1="England",
        latitude=51.5074,
        longitude=-0.1278,
        timezone="Europe/London",
    ),
    "Tokyo (Japan)": Location(
        name="Tokyo",
        country="Japan",
        admin1="Tokyo",
        latitude=35.6762,
        longitude=139.6503,
        timezone="Asia/Tokyo",
    ),
    "New York (USA)": Location(
        name="New York",
        country="United States",
        admin1="New York",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
    ),
}

# Persistent Disclaimers
PERSISTENT_DISCLAIMER = (
    "PROTOTYPE ONLY: This Rainfall Risk Indicator is a transparent heuristic for decision-support and preparedness. "
    "It is NOT a flood prediction or warning system and has not been officially validated. "
    "Always refer to the India Meteorological Department (IMD) and State Disaster Management Authorities (SDMA) for official meteorological warnings."
)

SCORE_NOT_ACCOUNTED_FOR: List[str] = [
    "Terrain slope, local elevation contours, and low-lying hollows",
    "Drainage capacity, stormwater network maintenance, and blockages",
    "Soil saturation, antecedent moisture conditions, and percolation rates",
    "River basin levels, upstream discharge, and catchment inflows",
    "Tidal surges, coastal storm tides, and estuarine backwater effects",
    "Dam and reservoir floodgate operations or emergency releases",
    "Local civil infrastructure conditions (culvert breaks, pump status)",
]

OFFICIAL_AUTHORITY_LINKS = {
    "India Meteorological Department (IMD)": "https://mausam.imd.gov.in",
    "Tamil Nadu State Disaster Management Authority (TNDSMA)": "https://tnsdma.tn.gov.in",
    "National Disaster Management Authority (NDMA India)": "https://ndma.gov.in",
    "World Meteorological Organization (WMO)": "https://wmo.int",
}
