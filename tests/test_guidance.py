"""Tests for guidance.py preparedness guidance, links, and brief formatting."""

import pytest
from models import ForecastData, RiskResult
from guidance import (
    TIERED_RECOMMENDATIONS,
    CHECKLIST_ITEMS,
    VERIFIED_OFFICIAL_LINKS,
    get_recommendations,
    build_brief,
)
from risk import compute_risk
from synthetic import generate_scenario


def test_every_category_has_both_languages():
    categories = ["Low", "Moderate", "High", "Severe"]
    for cat in categories:
        assert cat in TIERED_RECOMMENDATIONS
        recs_en = get_recommendations(cat, lang="en")
        recs_ta = get_recommendations(cat, lang="ta")

        assert len(recs_en) >= 3
        assert len(recs_ta) >= 3
        assert all(isinstance(r, str) and len(r) > 10 for r in recs_en)
        assert all(isinstance(r, str) and len(r) > 10 for r in recs_ta)


def test_checklist_structure():
    assert len(CHECKLIST_ITEMS) >= 5
    for item in CHECKLIST_ITEMS:
        assert "id" in item
        assert "category" in item
        assert "item_en" in item
        assert "item_ta" in item
        assert len(item["item_en"]) > 5
        assert len(item["item_ta"]) > 5


def test_official_links_verified():
    authority_names = [link["name"] for link in VERIFIED_OFFICIAL_LINKS]
    assert any("India Meteorological Department" in name for name in authority_names)
    assert any("Tamil Nadu State Disaster Management" in name for name in authority_names)
    assert any("National Disaster Management" in name for name in authority_names)
    assert any("World Meteorological Organization" in name for name in authority_names)

    for link in VERIFIED_OFFICIAL_LINKS:
        assert link["verified"] is True
        assert link["url"].startswith("http")


def test_build_brief_live_data(sample_forecast_data):
    risk = compute_risk(sample_forecast_data.hourly)
    brief = build_brief(sample_forecast_data, risk, lang="en")

    assert "CLIMATESHIELD AI" in brief
    assert "LIVE FORECAST" in brief
    assert "Chennai" in brief
    assert "Rainfall Risk Indicator" in brief
    assert "DISCLAIMER" in brief
    assert "1070" in brief
    assert "SYNTHETIC" not in brief


def test_build_brief_synthetic_data():
    synth_forecast = generate_scenario("Cyclone-style heavy burst", seed=42)
    risk = compute_risk(synth_forecast.hourly)
    brief = build_brief(synth_forecast, risk, lang="en")

    assert "SYNTHETIC DEMO DATA" in brief
    assert "synthetic scenario simulation" in brief
    assert "DISCLAIMER" in brief


def test_build_brief_tamil_language(sample_forecast_data):
    risk = compute_risk(sample_forecast_data.hourly)
    brief_ta = build_brief(sample_forecast_data, risk, lang="ta")

    # Should contain Tamil script in actions
    assert any(ord(char) >= 0x0B80 and ord(char) <= 0x0BFF for char in brief_ta)
    assert "பொறுப்புத் துறப்பு" in brief_ta
