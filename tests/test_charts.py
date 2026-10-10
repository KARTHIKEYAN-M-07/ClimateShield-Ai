"""Tests for charts.py Plotly visualization generation."""

import pytest
import plotly.graph_objects as go
import pandas as pd

from models import ForecastData, Location, DataQuality
from risk import compute_risk
from synthetic import generate_scenario
from charts import (
    plot_hourly_meteogram,
    plot_daily_summary,
    plot_cumulative_rainfall,
    plot_hourly_heatmap,
    plot_risk_contributions,
    plot_risk_gauge,
    plot_district_comparison,
)


def test_plot_hourly_meteogram_normal(sample_forecast_data):
    fig = plot_hourly_meteogram(sample_forecast_data)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 2  # bar + line


def test_plot_hourly_meteogram_synthetic():
    synth = generate_scenario("Cyclone-style heavy burst", seed=42)
    fig = plot_hourly_meteogram(synth)
    assert isinstance(fig, go.Figure)
    assert "SYNTHETIC DEMO" in fig.layout.title.text


def test_plot_hourly_meteogram_empty_and_none():
    fig1 = plot_hourly_meteogram(None)
    assert isinstance(fig1, go.Figure)

    empty_forecast = ForecastData(
        location=Location("Empty", "India", "TN", 13.0, 80.0, "UTC"),
        source="live",
        fetched_at_utc="2026-10-09T00:00:00Z",
        timezone="UTC",
        units={},
        hourly=pd.DataFrame(),
        daily=pd.DataFrame(),
        past_hours=0,
        quality=DataQuality(0.0),
    )
    fig2 = plot_hourly_meteogram(empty_forecast)
    assert isinstance(fig2, go.Figure)


def test_plot_daily_summary(sample_forecast_data):
    fig = plot_daily_summary(sample_forecast_data)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1

    fig_empty = plot_daily_summary(None)
    assert isinstance(fig_empty, go.Figure)


def test_plot_cumulative_rainfall(sample_forecast_data):
    fig = plot_cumulative_rainfall(sample_forecast_data)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1

    fig_empty = plot_cumulative_rainfall(None)
    assert isinstance(fig_empty, go.Figure)


def test_plot_hourly_heatmap(sample_forecast_data):
    fig = plot_hourly_heatmap(sample_forecast_data)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1

    fig_empty = plot_hourly_heatmap(None)
    assert isinstance(fig_empty, go.Figure)


def test_plot_risk_contributions(sample_forecast_data):
    risk = compute_risk(sample_forecast_data.hourly)
    fig = plot_risk_contributions(risk, is_synthetic=False)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1

    fig_empty = plot_risk_contributions(None)
    assert isinstance(fig_empty, go.Figure)


def test_plot_risk_gauge(sample_forecast_data):
    risk = compute_risk(sample_forecast_data.hourly)
    fig = plot_risk_gauge(risk, is_synthetic=False)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1

    fig_empty = plot_risk_gauge(None)
    assert isinstance(fig_empty, go.Figure)


def test_plot_district_comparison():
    districts = [
        {"name": "Chennai", "score": 65.0, "category": "High", "rain_72h": 120.0},
        {"name": "Madurai", "score": 20.0, "category": "Low", "rain_72h": 15.0},
        {"name": "Cuddalore", "score": 85.0, "category": "Severe", "rain_72h": 180.0},
    ]
    fig = plot_district_comparison(districts, is_synthetic=False)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1

    fig_empty = plot_district_comparison([])
    assert isinstance(fig_empty, go.Figure)
