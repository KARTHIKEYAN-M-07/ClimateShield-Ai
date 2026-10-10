"""ClimateShield AI: Transparent, explainable Rainfall Risk Indicator and preparedness dashboard.

Built with Streamlit. Thin presentation layer adhering strictly to the 8 always-on honesty rules.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from localization import category_label, translate

from models import Location, ForecastData, RiskConfig, RiskResult, FetchError
from config import (
    DEFAULT_CONFIG,
    PRESET_LOCATIONS,
    RISK_CATEGORIES,
    PERSISTENT_DISCLAIMER,
    SCORE_NOT_ACCOUNTED_FOR,
)
from data import fetch_forecast, search_locations, get_last_cached_forecast
from risk import compute_risk, find_peak_window, sensitivity, apply_scenario
from synthetic import generate_scenario, AVAILABLE_SCENARIOS, SCENARIO_DESCRIPTIONS
from guidance import (
    get_recommendations,
    CHECKLIST_ITEMS,
    VERIFIED_OFFICIAL_LINKS,
    build_brief,
)
from charts import (
    plot_hourly_meteogram,
    plot_daily_summary,
    plot_cumulative_rainfall,
    plot_hourly_heatmap,
    plot_risk_contributions,
    plot_risk_gauge,
    plot_district_comparison,
)

# Page configuration
st.set_page_config(
    page_title=translate("app.page_title", st.session_state.get("lang", "en")),
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _init_session_state() -> None:
    """Initialize session state variables."""
    if "lang" not in st.session_state:
        st.session_state.lang = "en"
    if "use_synthetic" not in st.session_state:
        st.session_state.use_synthetic = False
    if "synthetic_scenario" not in st.session_state:
        st.session_state.synthetic_scenario = "Cyclone-style heavy burst"
    if "synthetic_seed" not in st.session_state:
        st.session_state.synthetic_seed = 42
    if "risk_thresholds" not in st.session_state:
        st.session_state.risk_thresholds = dict(DEFAULT_CONFIG.thresholds)
    if "risk_weights" not in st.session_state:
        st.session_state.risk_weights = dict(DEFAULT_CONFIG.weights)
    if "what_if_multiplier" not in st.session_state:
        st.session_state.what_if_multiplier = 1.0


def tr(key: str, **values: object) -> str:
    """Translate a dashboard string using the persisted session language."""
    return translate(key, st.session_state.get("lang", "en"), **values)


def _localized_data_warning(warning: str, lang: str) -> str:
    """Translate known parser warnings while retaining technical field names and counts."""
    if lang != "ta":
        return warning
    if warning.startswith("Hourly payload missing or malformed"):
        return translate("overview.warning.malformed", lang)
    if warning.startswith("No hourly time steps"):
        return translate("overview.warning.no_times", lang)
    if warning.startswith("Missing field '"):
        field = warning.split("'", 2)[1]
        return translate("overview.warning.missing_field", lang, field=field)
    if warning.startswith("Mismatched length for '"):
        field = warning.split("'", 2)[1]
        details = warning.split("(", 1)[1].rstrip(".)")
        actual, expected = details.split(" vs expected ", 1)
        return translate("overview.warning.length", lang, field=field, actual=actual, expected=expected)
    if warning.startswith("SYNTHETIC DEMO DATA:"):
        return "செயற்கை மாதிரித் தரவு: விளக்கத்திற்காக உருவாக்கப்பட்ட சூழல்."
    return warning


def render_header(forecast: Optional[ForecastData]) -> None:
    """Render top header, status badges, and mandatory persistent disclaimer."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(tr("app.title"))
        st.caption(tr("app.subtitle"))
    with col2:
        if forecast:
            if forecast.source == "synthetic":
                st.warning(tr("status.synthetic" if st.session_state.lang == "ta" else "status.synthetic.en"))
            elif forecast.source == "cached":
                st.info(tr("status.cached" if st.session_state.lang == "ta" else "status.cached.en"))
            else:
                st.success(tr("status.live" if st.session_state.lang == "ta" else "status.live.en"))

    # Mandatory persistent disclaimer
    disclaimer = PERSISTENT_DISCLAIMER if st.session_state.lang == "en" else tr("disclaimer.body")
    heading = tr("disclaimer.en" if st.session_state.lang == "en" else "disclaimer.heading")
    st.info(f"{heading}: {disclaimer}")


def render_sidebar() -> Tuple[Location, int, int, RiskConfig]:
    """Render sidebar controls and return selected configuration."""
    st.sidebar.header(tr("sidebar.header"))

    # Language toggle
    selected_lang = st.sidebar.radio(
        tr("language.label"),
        options=["en", "ta"],
        index=0 if st.session_state.lang == "en" else 1,
        format_func=lambda code: translate("language.english" if code == "en" else "language.tamil", code),
        help=tr("language.help"),
        key="language_selector",
    )
    st.session_state.lang = selected_lang

    st.sidebar.markdown("---")

    # Synthetic Demo Mode Toggle
    use_synth = st.sidebar.checkbox(
        tr("sidebar.synthetic"),
        value=st.session_state.use_synthetic,
        help=tr("sidebar.synthetic_help"),
    )
    st.session_state.use_synthetic = use_synth

    if use_synth:
        st.sidebar.subheader(tr("sidebar.scenario_picker"))
        st.session_state.synthetic_scenario = st.sidebar.selectbox(
            tr("sidebar.scenario"),
            options=AVAILABLE_SCENARIOS,
            index=AVAILABLE_SCENARIOS.index(st.session_state.synthetic_scenario),
            format_func=lambda scenario: translate(
                "scenario.cyclone" if scenario == AVAILABLE_SCENARIOS[0] else "scenario.monsoon" if scenario == AVAILABLE_SCENARIOS[1] else "scenario.dry",
                st.session_state.lang,
            ),
        )
        scenario_description_key = {
            AVAILABLE_SCENARIOS[0]: "scenario.cyclone.description",
            AVAILABLE_SCENARIOS[1]: "scenario.monsoon.description",
            AVAILABLE_SCENARIOS[2]: "scenario.dry.description",
        }[st.session_state.synthetic_scenario]
        st.sidebar.caption(tr(scenario_description_key))
        st.session_state.synthetic_seed = st.sidebar.number_input(
            tr("sidebar.seed"),
            min_value=1,
            max_value=9999,
            value=st.session_state.synthetic_seed,
            step=1,
        )

    st.sidebar.markdown("---")

    # Location Selection
    st.sidebar.subheader(tr("sidebar.location"))
    mode_options = [tr("sidebar.presets"), tr("sidebar.place_search"), tr("sidebar.manual")]
    loc_mode = st.sidebar.radio(tr("sidebar.input_method"), mode_options, index=0)

    selected_location: Location = PRESET_LOCATIONS["Chennai (Tamil Nadu)"]

    if loc_mode == tr("sidebar.presets"):
        preset_names = list(PRESET_LOCATIONS.keys())
        choice = st.sidebar.selectbox(tr("sidebar.choose_location"), preset_names, index=0)
        selected_location = PRESET_LOCATIONS[choice]

    elif loc_mode == tr("sidebar.place_search"):
        query = st.sidebar.text_input(tr("sidebar.search"), "Madurai")
        if query:
            try:
                results = search_locations(query)
                if results:
                    loc_labels = [f"{loc.name}, {loc.admin1} ({loc.country})" for loc in results]
                    idx = st.sidebar.selectbox(
                        "பொருந்தும் இடத்தைத் தேர்ந்தெடுக்கவும்" if st.session_state.lang == "ta" else "Select Matching Location",
                        range(len(results)),
                        format_func=lambda i: loc_labels[i],
                    )
                    selected_location = results[idx]
                else:
                    st.sidebar.warning(f"{tr('sidebar.search_empty')} ({query})")
            except FetchError as err:
                st.sidebar.error(f"{tr('error.search_prefix')} {err.message}")

    elif loc_mode == tr("sidebar.manual"):
        c_lat, c_lon = st.sidebar.columns(2)
        lat = c_lat.number_input(tr("sidebar.latitude"), min_value=-90.0, max_value=90.0, value=13.0827, format="%.4f")
        lon = c_lon.number_input(tr("sidebar.longitude"), min_value=-180.0, max_value=180.0, value=80.2707, format="%.4f")
        selected_location = Location(
            name=f"Custom ({lat:.2f}, {lon:.2f})",
            country="Custom",
            admin1="Custom",
            latitude=float(lat),
            longitude=float(lon),
            timezone="auto",
        )

    # Forecast horizons
    st.sidebar.markdown("---")
    st.sidebar.subheader(tr("sidebar.horizon"))
    forecast_days = st.sidebar.slider(tr("sidebar.forecast_days"), min_value=1, max_value=7, value=3)
    past_days = st.sidebar.slider(tr("sidebar.past_days"), min_value=0, max_value=3, value=1)

    # Risk Config Sliders
    st.sidebar.markdown("---")
    with st.sidebar.expander(tr("sidebar.risk_settings"), expanded=False):
        st.caption(tr("sidebar.risk_help"))

        t_24h = st.slider(tr("sidebar.threshold_24h"), 30.0, 150.0, float(st.session_state.risk_thresholds["rain_24h_high"]), 5.0)
        t_72h = st.slider(tr("sidebar.threshold_72h"), 60.0, 300.0, float(st.session_state.risk_thresholds["rain_72h_high"]), 10.0)
        t_peak = st.slider(tr("sidebar.threshold_peak"), 5.0, 50.0, float(st.session_state.risk_thresholds["peak_intensity_high"]), 2.0)
        t_prob = st.slider(tr("sidebar.threshold_probability"), 50.0, 100.0, float(st.session_state.risk_thresholds["peak_prob_high"]), 5.0)
        t_wet = st.slider(tr("sidebar.threshold_wet_hours"), 4.0, 24.0, float(st.session_state.risk_thresholds["consecutive_wet_hours_high"]), 1.0)

        st.session_state.risk_thresholds["rain_24h_high"] = t_24h
        st.session_state.risk_thresholds["rain_72h_high"] = t_72h
        st.session_state.risk_thresholds["peak_intensity_high"] = t_peak
        st.session_state.risk_thresholds["peak_prob_high"] = t_prob
        st.session_state.risk_thresholds["consecutive_wet_hours_high"] = t_wet

        if st.button(tr("sidebar.reset")):
            st.session_state.risk_thresholds = dict(DEFAULT_CONFIG.thresholds)
            st.session_state.risk_weights = dict(DEFAULT_CONFIG.weights)
            st.rerun()

    active_config = RiskConfig(
        thresholds=st.session_state.risk_thresholds,
        weights=st.session_state.risk_weights,
    )

    return selected_location, forecast_days, past_days, active_config


def main() -> None:
    _init_session_state()
    location, forecast_days, past_days, active_config = render_sidebar()

    forecast: Optional[ForecastData] = None
    fetch_error: Optional[FetchError] = None

    # Load data (Synthetic or Live)
    if st.session_state.use_synthetic:
        forecast = generate_scenario(
            scenario_name=st.session_state.synthetic_scenario,
            location=location,
            seed=st.session_state.synthetic_seed,
            forecast_days=forecast_days,
        )
    else:
        try:
            forecast = fetch_forecast(
                location=location,
                forecast_days=forecast_days,
                past_days=past_days,
            )
        except FetchError as err:
            fetch_error = err
            # Check cached fallback
            cached = get_last_cached_forecast(location.latitude, location.longitude)
            if cached is not None:
                forecast = cached

    # Handle Fetch Error if no forecast could be resolved
    if fetch_error and forecast is None:
        render_header(None)
        failure_message = tr(f"error.{fetch_error.kind}")
        st.error(f"❌ **{tr('error.live_fetch')}** {failure_message}")
        with st.expander(tr("error.technical_details")):
            st.code(fetch_error.message)
        st.markdown(tr("error.troubleshooting"))
        c1, c2 = st.columns(2)
        if c1.button(tr("error.retry")):
            st.rerun()
        if c2.button(tr("error.enable_synthetic")):
            st.session_state.use_synthetic = True
            st.rerun()
        return

    # If fallback cache is used after an error, notify the user gently
    if fetch_error and forecast is not None:
        st.warning(f"⚠️ {tr('error.live_failed_cached')} {tr('error.detail_label')}: {fetch_error.message}")

    # Render header with active status
    render_header(forecast)

    # Compute risk
    past_hours = forecast.past_hours if forecast else 0
    # Apply what-if multiplier if active
    hourly_to_evaluate = forecast.hourly if forecast else pd.DataFrame()
    if st.session_state.what_if_multiplier != 1.0:
        hourly_to_evaluate = apply_scenario(hourly_to_evaluate, st.session_state.what_if_multiplier)

    risk_result = compute_risk(
        hourly_to_evaluate,
        config=active_config,
        past_hours=past_hours,
        lang=st.session_state.lang,
    )
    peak_window = find_peak_window(hourly_to_evaluate, past_hours=past_hours)
    sens_result = sensitivity(hourly_to_evaluate, config=active_config, past_hours=past_hours)

    is_synth = forecast.source == "synthetic" if forecast else False

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        tr("tab.overview"),
        tr("tab.charts"),
        tr("tab.risk"),
        tr("tab.preparedness"),
        tr("tab.compare"),
        tr("tab.about"),
    ])

    # ================= TAB 1: OVERVIEW =================
    with tab1:
        st.subheader(tr("overview.current_rating", place=location.name, region=location.admin1))

        col_g, col_m = st.columns([1, 1])
        with col_g:
            st.plotly_chart(plot_risk_gauge(risk_result, is_synthetic=is_synth, lang=st.session_state.lang), use_container_width=True)
        with col_m:
            st.markdown(f"### {tr('risk.category')}: **{category_label(risk_result.category, st.session_state.lang)}**")
            st.markdown(f"**{tr('risk.score')}:** `{risk_result.score:.1f} / 100`")
            st.markdown(f"**{tr('risk.explanation')}:** {risk_result.explanation}")

            # Metric counters
            precip_24h = forecast.hourly["precipitation"].iloc[:24].sum() if not forecast.hourly.empty else 0.0
            precip_72h = forecast.hourly["precipitation"].iloc[:72].sum() if not forecast.hourly.empty else 0.0
            max_prob = forecast.hourly["precipitation_probability"].max() if "precipitation_probability" in forecast.hourly.columns else 0.0

            m1, m2, m3 = st.columns(3)
            m1.metric(tr("metric.rain_24h"), f"{precip_24h:.1f} mm")
            m2.metric(tr("metric.rain_72h"), f"{precip_72h:.1f} mm")
            m3.metric(tr("metric.peak_probability"), f"{max_prob:.0f}%")

        st.markdown("---")
        # Peak 6-hour rainfall window & badges
        c_peak, c_sens, c_qual = st.columns(3)
        with c_peak:
            st.markdown(tr("overview.peak_window"))
            if peak_window["start_time"] != "N/A":
                st.write(f"**{tr('overview.period')}:** {peak_window['start_time']} - {peak_window['end_time']}")
                st.write(f"**{tr('overview.accumulation')}:** `{peak_window['total_rain_mm']:.1f} mm`")
                st.write(f"**{tr('overview.peak_intensity')}:** `{peak_window['peak_intensity_mm']:.1f} mm/h`")
            else:
                st.write(tr("overview.no_peak"))

        with c_sens:
            st.markdown(tr("overview.sensitivity"))
            sens_badge = tr("overview.stable") if sens_result["status"] == "stable" else tr("overview.borderline")
            st.write(f"**{tr('overview.status')}:** {sens_badge}")
            st.write(f"**{tr('overview.range')}:** `{sens_result['range']:.1f} pts`")
            st.caption(tr("overview.min_max", minimum=sens_result["min_score"], maximum=sens_result["max_score"]))

        with c_qual:
            st.markdown(tr("overview.quality"))
            q = forecast.quality if forecast else None
            q_pct = q.completeness_pct if q else 100.0
            st.write(f"**{tr('overview.completeness')}:** `{q_pct:.1f}%`")
            if q and q.warnings:
                st.caption(f"{tr('overview.notes')}: {'; '.join(_localized_data_warning(w, st.session_state.lang) for w in q.warnings[:2])}")
            else:
                st.write(tr("overview.fields_valid"))

    # ================= TAB 2: CHARTS =================
    with tab2:
        st.subheader(tr("charts.heading"))
        st.plotly_chart(plot_hourly_meteogram(forecast, lang=st.session_state.lang), use_container_width=True)

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.plotly_chart(plot_cumulative_rainfall(forecast, lang=st.session_state.lang), use_container_width=True)
        with col_c2:
            st.plotly_chart(plot_daily_summary(forecast, lang=st.session_state.lang), use_container_width=True)

        st.plotly_chart(plot_hourly_heatmap(forecast, lang=st.session_state.lang), use_container_width=True)

    # ================= TAB 3: RISK EXPLAINED =================
    with tab3:
        st.subheader(tr("risk.breakdown"))
        st.plotly_chart(plot_risk_contributions(risk_result, is_synthetic=is_synth, lang=st.session_state.lang), use_container_width=True)

        # What-if scenario stress-testing
        st.markdown(tr("risk.what_if"))
        st.caption(tr("risk.what_if_help"))
        mult = st.select_slider(
            tr("risk.multiplier"),
            options=[1.0, 1.25, 1.5],
            value=st.session_state.what_if_multiplier,
            format_func=lambda x: f"x{x:.2f} ({tr('risk.baseline') if x == 1.0 else tr('risk.hypothetical')})",
        )
        if mult != st.session_state.what_if_multiplier:
            st.session_state.what_if_multiplier = mult
            st.rerun()

        if st.session_state.what_if_multiplier > 1.0:
            st.warning(tr("risk.multiplier_warning", multiplier=st.session_state.what_if_multiplier))

        # Active thresholds table
        st.markdown(tr("risk.thresholds"))
        thresh_df = pd.DataFrame([
            {tr("risk.factor"): translate(f"chart.risk_factor.{factor}", st.session_state.lang), tr("risk.threshold"): f"{active_config.thresholds[threshold]} {unit}", tr("risk.weight"): f"{active_config.weights[weight]*100:.0f}%", tr("risk.points"): f"{risk_result.contributions.get(factor, 0):.1f}"}
            for factor, threshold, weight, unit in [
                ("rain_24h", "rain_24h_high", "weight_24h", "mm"),
                ("rain_72h", "rain_72h_high", "weight_72h", "mm"),
                ("peak_intensity", "peak_intensity_high", "weight_peak_intensity", "mm/h"),
                ("peak_prob", "peak_prob_high", "weight_peak_prob", "%"),
                ("consecutive_wet_hours", "consecutive_wet_hours_high", "weight_consecutive", "h"),
            ]
        ])
        st.table(thresh_df)

        # What the score ignores
        st.markdown(tr("risk.omissions"))
        st.caption(tr("risk.omissions_help"))
        omissions = ["terrain", "drainage", "soil", "river", "tide", "dam", "infrastructure"]
        for item in omissions:
            st.markdown(f"- ❌ **{translate(f'risk.omission.{item}', st.session_state.lang)}**")

    # ================= TAB 4: PREPAREDNESS =================
    with tab4:
        st.subheader(tr("preparedness.heading"))
        lang = st.session_state.lang

        # Recommendations
        st.markdown(tr("preparedness.actions", category=category_label(risk_result.category, lang)))
        recs = get_recommendations(risk_result.category, lang=lang)
        for r in recs:
            st.markdown(f"- ✅ {r}")

        st.markdown("---")

        # Emergency Checklist
        st.markdown(tr("preparedness.checklist"))
        st.caption(tr("preparedness.checklist_help"))
        for item in CHECKLIST_ITEMS:
            item_text = item["item_ta"] if lang == "ta" else item["item_en"]
            category_key = {"Household Kit": "household", "Documents": "documents", "Power & Tech": "power", "Family Care": "family", "Route Awareness": "routes"}[item["category"]]
            category_text = translate(f"preparedness.category.{category_key}", lang)
            st.checkbox(f"{category_text}: {item_text}", key=f"chk_{item['id']}")

        st.markdown("---")

        # Official disaster links
        st.markdown(tr("preparedness.authorities"))
        for l in VERIFIED_OFFICIAL_LINKS:
            link_key = {"India Meteorological Department (IMD)": "imd", "Tamil Nadu State Disaster Management Authority (TNDSMA)": "tnsdma", "National Disaster Management Authority (NDMA India)": "ndma", "World Meteorological Organization (WMO)": "wmo", "World Weather Information Service (WWIS)": "wwis"}[l["name"]]
            scope_key = {"National (India)": "national_india", "State (Tamil Nadu)": "state_tamil_nadu", "International": "international", "International Pointer": "international_pointer"}[l["scope"]]
            st.markdown(f"- **[{l['name']}]({l['url']})** ({translate(f'preparedness.scope.{scope_key}', lang)}): {translate(f'preparedness.link.{link_key}', lang)}")

        st.markdown("---")

        # WhatsApp-ready Brief
        st.markdown(tr("preparedness.brief"))
        brief_text = build_brief(forecast, risk_result, lang=lang)
        st.text_area(tr("preparedness.brief_label"), value=brief_text, height=220)

        prefix_dl = "SYNTHETIC_" if is_synth else ""
        st.download_button(
            label=tr("preparedness.download_brief"),
            data=brief_text,
            file_name=f"{prefix_dl}ClimateShield_Brief_{location.name}.txt",
            mime="text/plain",
        )

    # ================= TAB 5: COMPARE DISTRICTS =================
    with tab5:
        st.subheader(tr("comparison.heading"))
        st.caption(tr("comparison.help"))

        tn_keys = [k for k in PRESET_LOCATIONS.keys() if "Tamil Nadu" in k]
        
        # Build comparison dataset
        comparison_results: List[Dict[str, Any]] = []
        map_lats: List[float] = []
        map_lons: List[float] = []
        map_texts: List[str] = []
        map_colors: List[str] = []

        with st.spinner(tr("comparison.loading")):
            for key in tn_keys:
                loc = PRESET_LOCATIONS[key]
                try:
                    if is_synth:
                        d_fc = generate_scenario("Cyclone-style heavy burst", location=loc, seed=42)
                    else:
                        d_fc = fetch_forecast(loc, forecast_days=3, past_days=0)
                    
                    d_risk = compute_risk(d_fc.hourly, config=active_config)
                    r72 = float(d_fc.hourly["precipitation"].iloc[:72].sum())
                    
                    comparison_results.append({
                        "name": loc.name,
                        "score": d_risk.score,
                        "category": d_risk.category,
                        "rain_72h": r72,
                    })

                    map_lats.append(loc.latitude)
                    map_lons.append(loc.longitude)
                    cat_color = RISK_CATEGORIES.get(d_risk.category, {}).get("color", "#6b7280")
                    map_colors.append(cat_color)
                    map_texts.append(f"<b>{loc.name}</b><br>{tr('chart.category')}: {category_label(d_risk.category, st.session_state.lang)} ({d_risk.score:.1f}/100)<br>{tr('chart.rain_72h')}: {r72:.1f} mm")
                except FetchError:
                    # Non-fatal per-row failure
                    comparison_results.append({
                        "name": loc.name,
                        "score": 0.0,
                        "category": "Error",
                        "rain_72h": 0.0,
                    })

        col_cmp_chart, col_cmp_map = st.columns([1, 1])
        with col_cmp_chart:
            st.plotly_chart(plot_district_comparison(comparison_results, is_synthetic=is_synth, lang=st.session_state.lang), use_container_width=True)

        with col_cmp_map:
            st.markdown(tr("comparison.map"))
            # Plotly scattergeo map without map token
            fig_map = go.Figure()
            fig_map.add_trace(
                go.Scattergeo(
                    lat=map_lats,
                    lon=map_lons,
                    mode="markers+text",
                    marker=dict(size=14, color=map_colors, line=dict(width=1, color="black")),
                    text=[d["name"] for d in comparison_results if d["category"] != "Error"],
                    textposition="top center",
                    hovertext=map_texts,
                    hoverinfo="text",
                )
            )
            fig_map.update_layout(
                geo=dict(
                    center=dict(lat=11.1271, lon=78.6569),
                    projection_scale=14,
                    showland=True,
                    landcolor="rgb(240, 240, 240)",
                    countrycolor="rgb(200, 200, 200)",
                    showsubunits=True,
                ),
                margin=dict(l=0, r=0, t=30, b=0),
                height=380,
            )
            st.plotly_chart(fig_map, use_container_width=True)

    # ================= TAB 6: ABOUT & DATA =================
    with tab6:
        st.subheader(tr("about.heading"))
        st.markdown(tr("about.source"))

        st.markdown(tr("about.timestamps"))
        st.write(f"- **{tr('about.fetched_at')}:** `{forecast.fetched_at_utc}`")
        st.write(f"- **{tr('about.timezone')}:** `{forecast.timezone}`")
        st.write(f"- **{tr('about.units')}:** `{forecast.units}`")

        # CSV Download
        st.markdown(tr("about.download"))
        csv_buffer = io.StringIO()
        forecast.hourly.to_csv(csv_buffer, index=False)
        prefix_csv = "SYNTHETIC_" if is_synth else ""
        st.download_button(
            label=tr("about.download_csv"),
            data=csv_buffer.getvalue(),
            file_name=f"{prefix_csv}precipitation_forecast_{location.name}.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
