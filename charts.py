"""Plotly visualization functions for ClimateShield AI.

Generates responsive, publication-quality Plotly figures:
- Hourly meteogram (precip bars + probability line on secondary y-axis)
- Daily summary bar chart
- Cumulative rainfall curve with 24/48/72h milestone markers
- Hour-by-day precipitation intensity heatmap
- Risk factor contribution decomposition bar chart
- Risk indicator gauge with category bands and status label
- Multi-district comparative risk ranking chart

Every function gracefully handles empty/partial data and automatically labels
titles with '[SYNTHETIC DEMO]' when synthetic data is active.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from models import ForecastData, RiskResult
from config import RISK_CATEGORIES
from localization import category_label, translate

# Common styling palette
CHART_BG_COLOR = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(128,128,128,0.2)"
TEXT_COLOR = "#1f2937"


def _empty_figure(title: str, lang: str = "en") -> go.Figure:
    """Helper to return an empty placeholder figure with a descriptive title."""
    fig = go.Figure()
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": translate("chart.empty", lang),
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 14, "color": "gray"},
            }
        ],
        paper_bgcolor=CHART_BG_COLOR,
        plot_bgcolor=CHART_BG_COLOR,
        margin={"l": 40, "r": 40, "t": 60, "b": 40},
    )
    return fig


def _synthetic_prefix(is_synthetic: bool, lang: str = "en") -> str:
    """Returns [SYNTHETIC DEMO] badge prefix if synthetic."""
    if not is_synthetic:
        return ""
    return "[செயற்கை மாதிரி] " if lang == "ta" else "[SYNTHETIC DEMO] "


def plot_hourly_meteogram(forecast: Optional[ForecastData], lang: str = "en") -> go.Figure:
    """Dual-axis hourly meteogram: precipitation bars with probability line on secondary Y-axis."""
    if forecast is None or forecast.hourly is None or forecast.hourly.empty:
        return _empty_figure(f"{translate('chart.hourly_title', lang)} ({translate('chart.no_data', lang)})", lang)

    df = forecast.hourly
    is_synth = forecast.source == "synthetic"
    prefix = _synthetic_prefix(is_synth, lang)
    title = f"{prefix}{translate('chart.hourly_title', lang)}"

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Precipitation bars
    precip_unit = forecast.units.get("precipitation", "mm")
    fig.add_trace(
        go.Bar(
            x=df["time"],
            y=df["precipitation"],
            name=translate("chart.hourly_rain", lang, unit=precip_unit),
            marker_color="#2563eb",
            opacity=0.85,
            hovertemplate=f"%{{x}}<br>{translate('chart.rainfall', lang)}: %{{y:.1f}} {precip_unit}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Probability line
    if "precipitation_probability" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["precipitation_probability"],
                name=translate("chart.rain_probability", lang),
                line=dict(color="#f97316", width=2.5),
                mode="lines+markers",
                marker=dict(size=4),
                hovertemplate=f"%{{x}}<br>{translate('chart.probability', lang)}: %{{y:.0f}}%<extra></extra>",
            ),
            secondary_y=True,
        )

    fig.update_layout(
        title={"text": title, "x": 0.05, "xanchor": "left"},
        paper_bgcolor=CHART_BG_COLOR,
        plot_bgcolor=CHART_BG_COLOR,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
        margin={"l": 50, "r": 50, "t": 70, "b": 40},
    )

    fig.update_xaxes(title_text=translate("chart.time", lang), showgrid=True, gridcolor=GRID_COLOR)
    fig.update_yaxes(
        title_text=translate("chart.precipitation", lang, unit=precip_unit),
        secondary_y=False,
        showgrid=True,
        gridcolor=GRID_COLOR,
        rangemode="nonnegative",
    )
    fig.update_yaxes(
        title_text=translate("chart.rain_probability", lang),
        secondary_y=True,
        showgrid=False,
        range=[0, 105],
    )

    return fig


def plot_daily_summary(forecast: Optional[ForecastData], lang: str = "en") -> go.Figure:
    """Daily summary bar chart with rainfall totals and max probabilities."""
    if forecast is None or forecast.daily is None or forecast.daily.empty:
        return _empty_figure(f"{translate('chart.daily_title', lang)} ({translate('chart.no_data', lang)})", lang)

    df = forecast.daily
    is_synth = forecast.source == "synthetic"
    prefix = _synthetic_prefix(is_synth, lang)
    unit = forecast.units.get("precipitation_sum", "mm")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["precipitation_sum"],
            name=translate("chart.daily_total", lang, unit=unit),
            marker_color="#0284c7",
            text=df["precipitation_sum"].apply(lambda v: f"{v:.1f} {unit}"),
            textposition="auto",
            hovertemplate=f"%{{x}}<br>{translate('chart.accumulation', lang)}: %{{y:.1f}} {unit}<extra></extra>",
        )
    )

    fig.update_layout(
        title={"text": f"{prefix}{translate('chart.daily_title', lang)}", "x": 0.05, "xanchor": "left"},
        paper_bgcolor=CHART_BG_COLOR,
        plot_bgcolor=CHART_BG_COLOR,
        margin={"l": 50, "r": 50, "t": 60, "b": 40},
    )
    fig.update_xaxes(title_text=translate("chart.date", lang), showgrid=True, gridcolor=GRID_COLOR)
    fig.update_yaxes(title_text=translate("chart.total_rain", lang, unit=unit), showgrid=True, gridcolor=GRID_COLOR, rangemode="nonnegative")
    return fig


def plot_cumulative_rainfall(forecast: Optional[ForecastData], lang: str = "en") -> go.Figure:
    """Cumulative rainfall accumulation curve with 24h, 48h, and 72h markers."""
    if forecast is None or forecast.hourly is None or forecast.hourly.empty:
        return _empty_figure(f"{translate('chart.cumulative_title', lang)} ({translate('chart.no_data', lang)})", lang)

    df = forecast.hourly.copy()
    unit = forecast.units.get("precipitation", "mm")
    df["cumulative"] = df["precipitation"].cumsum()

    is_synth = forecast.source == "synthetic"
    prefix = _synthetic_prefix(is_synth, lang)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["cumulative"],
            name=translate("chart.cumulative_rain", lang),
            line=dict(color="#059669", width=3),
            fill="tozeroy",
            fillcolor="rgba(16, 185, 129, 0.15)",
            hovertemplate=f"%{{x}}<br>{translate('chart.cumulative', lang)}: %{{y:.1f}} {unit}<extra></extra>",
        )
    )

    # Add milestone markers for 24h, 48h, 72h
    milestones = [24, 48, 72]
    for h in milestones:
        if h <= len(df):
            row = df.iloc[h - 1]
            val = row["cumulative"]
            time_val = row["time"]
            fig.add_trace(
                go.Scatter(
                    x=[time_val],
                    y=[val],
                    mode="markers+text",
                    marker=dict(size=10, color="#dc2626"),
                    text=[f"{h}h: {val:.1f}{unit}"],
                    textposition="top center",
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    fig.update_layout(
        title={"text": f"{prefix}{translate('chart.cumulative_title', lang)}", "x": 0.05, "xanchor": "left"},
        paper_bgcolor=CHART_BG_COLOR,
        plot_bgcolor=CHART_BG_COLOR,
        margin={"l": 50, "r": 50, "t": 60, "b": 40},
    )
    fig.update_xaxes(title_text=translate("chart.time", lang), showgrid=True, gridcolor=GRID_COLOR)
    fig.update_yaxes(title_text=f"{translate('chart.cumulative_rain', lang)} ({unit})", showgrid=True, gridcolor=GRID_COLOR, rangemode="nonnegative")
    return fig


def plot_hourly_heatmap(forecast: Optional[ForecastData], lang: str = "en") -> go.Figure:
    """Hour-of-day vs Date precipitation intensity heatmap."""
    if forecast is None or forecast.hourly is None or forecast.hourly.empty:
        return _empty_figure(f"{translate('chart.heatmap_title', lang)} ({translate('chart.no_data', lang)})", lang)

    df = forecast.hourly.copy()
    try:
        df["dt"] = pd.to_datetime(df["time"])
        df["date"] = df["dt"].dt.strftime("%Y-%m-%d")
        df["hour"] = df["dt"].dt.hour
        pivot = df.pivot_table(index="date", columns="hour", values="precipitation", aggfunc="first").fillna(0.0)
    except Exception:
        return _empty_figure(f"{translate('chart.heatmap_title', lang)} ({translate('chart.parse_error', lang)})", lang)

    if pivot.empty:
        return _empty_figure(f"{translate('chart.heatmap_title', lang)} ({translate('chart.no_data', lang)})", lang)

    is_synth = forecast.source == "synthetic"
    prefix = _synthetic_prefix(is_synth, lang)
    unit = forecast.units.get("precipitation", "mm")

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=[f"{h:02d}:00" for h in pivot.columns],
            y=pivot.index.tolist(),
            colorscale="Tealgrn",
            hoverongaps=False,
            hovertemplate=f"{translate('chart.date', lang)}: %{{y}}<br>{translate('chart.hour', lang)}: %{{x}}<br>{translate('chart.rainfall', lang)}: %{{z:.1f}} {unit}<extra></extra>",
            colorbar=dict(title=unit),
        )
    )

    fig.update_layout(
        title={"text": f"{prefix}{translate('chart.heatmap_title', lang)}", "x": 0.05, "xanchor": "left"},
        xaxis_title=translate("chart.heatmap_hour", lang),
        yaxis_title=translate("chart.date", lang),
        paper_bgcolor=CHART_BG_COLOR,
        plot_bgcolor=CHART_BG_COLOR,
        margin={"l": 80, "r": 40, "t": 60, "b": 40},
    )
    return fig


def plot_risk_contributions(risk: Optional[RiskResult], is_synthetic: bool = False, lang: str = "en") -> go.Figure:
    """Horizontal bar chart decomposing the risk score into factor contributions."""
    if risk is None or not risk.contributions:
        return _empty_figure(f"{translate('chart.rainfall_contributions_title', lang)} ({translate('chart.no_data', lang)})", lang)

    prefix = _synthetic_prefix(is_synthetic, lang)
    labels_map = {
        key: translate(f"chart.risk_factor.{key}", lang)
        for key in ("rain_24h", "rain_72h", "peak_intensity", "peak_prob", "consecutive_wet_hours", "recent_rain")
    }

    names = [labels_map.get(k, k) for k in risk.contributions.keys()]
    values = list(risk.contributions.values())

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=names,
            x=values,
            orientation="h",
            marker_color="#6366f1",
            text=[f"{v:.1f} {translate('chart.points', lang)}" for v in values],
            textposition="auto",
            hovertemplate=f"%{{y}}: %{{x:.1f}} {translate('chart.points', lang)}<extra></extra>",
        )
    )

    fig.update_layout(
        title={"text": f"{prefix}{translate('chart.rainfall_contributions_title', lang)}", "x": 0.05, "xanchor": "left"},
        paper_bgcolor=CHART_BG_COLOR,
        plot_bgcolor=CHART_BG_COLOR,
        margin={"l": 160, "r": 40, "t": 60, "b": 40},
    )
    fig.update_xaxes(title_text=translate("chart.contribution_points", lang), showgrid=True, gridcolor=GRID_COLOR, range=[0, max(35.0, max(values) + 5)])
    return fig


def plot_risk_gauge(risk: Optional[RiskResult], is_synthetic: bool = False, lang: str = "en") -> go.Figure:
    """Gauge indicator chart showing the Rainfall Risk Indicator score and category."""
    if risk is None:
        return _empty_figure(f"{translate('chart.gauge_title', lang)} ({translate('chart.no_data', lang)})", lang)

    score = risk.score
    cat = risk.category
    cat_info = RISK_CATEGORIES.get(cat, {"color": "#6b7280", "badge": cat})
    prefix = _synthetic_prefix(is_synthetic, lang)
    badge = cat_info["badge"].replace(cat, category_label(cat, lang))

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            title={"text": f"{prefix}{translate('chart.gauge_title', lang)}: {badge}", "font": {"size": 20}},
            number={"suffix": "/100", "font": {"size": 36, "color": cat_info["color"]}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "gray"},
                "bar": {"color": cat_info["color"], "thickness": 0.3},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, 25], "color": "rgba(34, 197, 94, 0.25)"},
                    {"range": [25, 50], "color": "rgba(234, 179, 8, 0.25)"},
                    {"range": [50, 75], "color": "rgba(249, 115, 22, 0.25)"},
                    {"range": [75, 100], "color": "rgba(239, 68, 68, 0.25)"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "thickness": 0.75,
                    "value": score,
                },
            },
        )
    )

    fig.update_layout(
        paper_bgcolor=CHART_BG_COLOR,
        plot_bgcolor=CHART_BG_COLOR,
        height=320,
        margin={"l": 30, "r": 30, "t": 60, "b": 20},
    )
    return fig


def plot_district_comparison(
    districts: List[Dict[str, Any]],
    is_synthetic: bool = False,
    lang: str = "en",
) -> go.Figure:
    """Horizontal bar chart comparing risk scores across districts."""
    if not districts:
        return _empty_figure(f"{translate('chart.district_title', lang)} ({translate('chart.no_data', lang)})", lang)

    prefix = _synthetic_prefix(is_synthetic, lang)
    # Sort descending by score
    sorted_districts = sorted(districts, key=lambda d: d.get("score", 0.0))

    names = [d.get("name", "Unknown") for d in sorted_districts]
    scores = [d.get("score", 0.0) for d in sorted_districts]
    categories = [d.get("category", "Low") for d in sorted_districts]
    colors = [RISK_CATEGORIES.get(cat, {}).get("color", "#6b7280") for cat in categories]
    hover_texts = [
        f"<b>{d.get('name')}</b><br>{translate('chart.score', lang)}: {d.get('score', 0):.1f}/100<br>{translate('chart.category', lang)}: {category_label(d.get('category', 'Low'), lang)}<br>{translate('chart.rain_72h', lang)}: {d.get('rain_72h', 0):.1f} mm"
        for d in sorted_districts
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=names,
            x=scores,
            orientation="h",
            marker_color=colors,
            text=[f"{s:.1f} ({category_label(c, lang)})" for s, c in zip(scores, categories)],
            textposition="auto",
            hovertext=hover_texts,
            hoverinfo="text",
        )
    )

    fig.update_layout(
        title={"text": f"{prefix}{translate('chart.district_title', lang)}", "x": 0.05, "xanchor": "left"},
        paper_bgcolor=CHART_BG_COLOR,
        plot_bgcolor=CHART_BG_COLOR,
        margin={"l": 120, "r": 40, "t": 60, "b": 40},
    )
    fig.update_xaxes(title_text=translate("chart.score", lang), showgrid=True, gridcolor=GRID_COLOR, range=[0, 105])
    return fig
