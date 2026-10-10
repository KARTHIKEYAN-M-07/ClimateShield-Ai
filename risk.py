"""Risk engine for ClimateShield AI: transparent rule-based heuristic indicator.

Pure functions with NO Streamlit dependencies. Computes the Rainfall Risk Indicator
(Low, Moderate, High, Severe) alongside factor contributions, drivers, plain-language
explanations, peak 6-hour window identification, sensitivity testing, and scenario stress tests.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import pandas as pd

from models import RiskConfig, RiskResult
from config import DEFAULT_CONFIG, SCORE_NOT_ACCOUNTED_FOR
from localization import category_label, translate


def _calculate_consecutive_wet_hours(precip_series: pd.Series, wet_threshold: float = 1.0) -> float:
    """Compute the longest continuous sequence of hours with precipitation >= wet_threshold."""
    max_run = 0
    current_run = 0
    for val in precip_series:
        if val >= wet_threshold:
            current_run += 1
            if current_run > max_run:
                max_run = current_run
        else:
            current_run = 0
    return float(max_run)


def calculate_factors(hourly: pd.DataFrame, past_hours: int = 0) -> Dict[str, float]:
    """Extract raw meteorological risk factors from hourly precipitation data."""
    if hourly is None or hourly.empty:
        return {
            "rain_24h": 0.0,
            "rain_72h": 0.0,
            "peak_intensity": 0.0,
            "peak_prob": 0.0,
            "consecutive_wet_hours": 0.0,
            "recent_rain": 0.0,
        }

    # Separate recent context and forecast slice
    total_len = len(hourly)
    safe_past = max(0, min(past_hours, total_len))
    
    if safe_past > 0:
        recent_df = hourly.iloc[:safe_past]
        forecast_df = hourly.iloc[safe_past:]
    else:
        recent_df = pd.DataFrame()
        forecast_df = hourly

    precip_col = forecast_df["precipitation"] if "precipitation" in forecast_df.columns else pd.Series(dtype=float)
    prob_col = forecast_df["precipitation_probability"] if "precipitation_probability" in forecast_df.columns else pd.Series(dtype=float)

    # 24h accumulation
    rain_24h = float(precip_col.iloc[:24].sum()) if len(precip_col) > 0 else 0.0

    # 72h accumulation
    rain_72h = float(precip_col.iloc[:72].sum()) if len(precip_col) > 0 else 0.0

    # Peak intensity
    peak_intensity = float(precip_col.max()) if len(precip_col) > 0 and not precip_col.isna().all() else 0.0

    # Peak probability
    peak_prob = float(prob_col.max()) if len(prob_col) > 0 and not prob_col.isna().all() else 0.0

    # Consecutive wet hours
    consecutive_wet_hours = _calculate_consecutive_wet_hours(precip_col) if len(precip_col) > 0 else 0.0

    # Recent rain in past_hours
    recent_rain = 0.0
    if not recent_df.empty and "precipitation" in recent_df.columns:
        recent_rain = float(recent_df["precipitation"].sum())

    return {
        "rain_24h": max(0.0, rain_24h),
        "rain_72h": max(0.0, rain_72h),
        "peak_intensity": max(0.0, peak_intensity),
        "peak_prob": max(0.0, min(100.0, peak_prob)),
        "consecutive_wet_hours": max(0.0, consecutive_wet_hours),
        "recent_rain": max(0.0, recent_rain),
    }


def compute_risk(
    hourly: pd.DataFrame,
    config: RiskConfig = DEFAULT_CONFIG,
    past_hours: int = 0,
    lang: str = "en",
) -> RiskResult:
    """Compute the transparent rule-based Rainfall Risk Indicator."""
    raw_factors = calculate_factors(hourly, past_hours=past_hours)
    thresholds = config.thresholds
    weights = config.weights

    # Map factor names to config keys
    factor_mapping = {
        "rain_24h": ("rain_24h_high", "weight_24h", "risk.driver.rain_24h", "mm"),
        "rain_72h": ("rain_72h_high", "weight_72h", "risk.driver.rain_72h", "mm"),
        "peak_intensity": ("peak_intensity_high", "weight_peak_intensity", "risk.driver.peak_intensity", "mm/h"),
        "peak_prob": ("peak_prob_high", "weight_peak_prob", "risk.driver.peak_prob", "%"),
        "consecutive_wet_hours": ("consecutive_wet_hours_high", "weight_consecutive", "risk.driver.consecutive_wet_hours", "h"),
        "recent_rain": ("recent_rain_high", "weight_recent", "risk.driver.recent_rain", "mm"),
    }

    # If no past hours context is provided, exclude recent_rain from active weight calculation
    active_factor_keys = ["rain_24h", "rain_72h", "peak_intensity", "peak_prob", "consecutive_wet_hours"]
    if past_hours > 0:
        active_factor_keys.append("recent_rain")

    total_active_weight = sum(weights.get(factor_mapping[k][1], 0.0) for k in active_factor_keys)
    contributions: Dict[str, float] = {}
    driver_candidates: List[Tuple[float, str]] = []

    total_points = 0.0
    for f_key, (thresh_key, weight_key, label, unit) in factor_mapping.items():
        val = raw_factors[f_key]
        thresh = thresholds.get(thresh_key, 1.0)
        weight = weights.get(weight_key, 0.0)

        # Normalize 0.0 - 1.0
        norm_score = min(1.0, max(0.0, val / thresh)) if thresh > 0 else 0.0
        
        # Scale by active weight proportion so all active factors sum to 100.0 max
        if f_key in active_factor_keys and total_active_weight > 0:
            effective_weight = weight / total_active_weight
        else:
            effective_weight = 0.0
            
        unrounded_points = norm_score * effective_weight * 100.0
        total_points += unrounded_points
        weighted_points = round(unrounded_points, 1)
        contributions[f_key] = weighted_points

        # Store driver description if relevant
        if f_key in active_factor_keys:
            driver_desc = f"{translate(label, lang)}: {val:.1f} {unit} ({weighted_points:.1f} pts)"
            driver_candidates.append((weighted_points, driver_desc))

    # Calculate overall score
    clamped_score = max(0.0, min(100.0, round(total_points, 1)))

    # Determine risk category
    if clamped_score < 25.0:
        category = "Low"
    elif clamped_score < 50.0:
        category = "Moderate"
    elif clamped_score < 75.0:
        category = "High"
    else:
        category = "Severe"

    # Select top 2-3 drivers (highest contribution points)
    driver_candidates.sort(key=lambda x: x[0], reverse=True)
    top_drivers = [desc for pts, desc in driver_candidates[:3] if pts > 0.0]
    if not top_drivers:
        top_drivers = [translate("risk.driver.minimal", lang)]

    # Construct plain-language explanation
    explanation = translate(
        "risk.explanation_template",
        lang,
        category=category_label(category, lang),
        score=clamped_score,
        drivers="; ".join(top_drivers[:2]),
    )

    return RiskResult(
        score=clamped_score,
        category=category,
        contributions=contributions,
        drivers=top_drivers,
        explanation=explanation,
        not_accounted_for=list(SCORE_NOT_ACCOUNTED_FOR),
    )


def find_peak_window(hourly: pd.DataFrame, past_hours: int = 0) -> Dict[str, Any]:
    """Identify the heaviest rolling 6-hour rainfall block in the forecast."""
    default_result = {
        "start_time": "N/A",
        "end_time": "N/A",
        "total_rain_mm": 0.0,
        "peak_intensity_mm": 0.0,
    }

    if hourly is None or hourly.empty or "precipitation" not in hourly.columns:
        return default_result

    total_len = len(hourly)
    safe_past = max(0, min(past_hours, total_len))
    forecast_df = hourly.iloc[safe_past:].reset_index(drop=True)

    if forecast_df.empty:
        return default_result

    if len(forecast_df) < 6:
        # Less than 6 hours available: use all available
        total = float(forecast_df["precipitation"].sum())
        peak = float(forecast_df["precipitation"].max())
        return {
            "start_time": str(forecast_df["time"].iloc[0]),
            "end_time": str(forecast_df["time"].iloc[-1]),
            "total_rain_mm": round(total, 1),
            "peak_intensity_mm": round(peak, 1),
        }

    rolling_sums = forecast_df["precipitation"].rolling(window=6).sum()
    max_idx = rolling_sums.idxmax()

    if pd.isna(max_idx):
        return default_result

    start_idx = max(0, int(max_idx) - 5)
    end_idx = int(max_idx)
    window_slice = forecast_df.iloc[start_idx : end_idx + 1]

    return {
        "start_time": str(window_slice["time"].iloc[0]),
        "end_time": str(window_slice["time"].iloc[-1]),
        "total_rain_mm": round(float(rolling_sums.loc[max_idx]), 1),
        "peak_intensity_mm": round(float(window_slice["precipitation"].max()), 1),
    }


def sensitivity(
    hourly: pd.DataFrame,
    config: RiskConfig = DEFAULT_CONFIG,
    past_hours: int = 0,
) -> Dict[str, Any]:
    """Test indicator sensitivity under +/-20% perturbations on weights and thresholds."""
    base_res = compute_risk(hourly, config=config, past_hours=past_hours)
    base_score = base_res.score

    perturbed_scores: List[float] = [base_score]

    # Perturb thresholds by +20% and -20%
    for factor in [+0.20, -0.20]:
        perturbed_thresholds = {k: v * (1.0 + factor) for k, v in config.thresholds.items()}
        cfg = RiskConfig(thresholds=perturbed_thresholds, weights=config.weights)
        score = compute_risk(hourly, config=cfg, past_hours=past_hours).score
        perturbed_scores.append(score)

    # Perturb weights by +20% and -20%
    for factor in [+0.20, -0.20]:
        perturbed_weights = {k: v * (1.0 + factor) for k, v in config.weights.items()}
        cfg = RiskConfig(thresholds=config.thresholds, weights=perturbed_weights)
        score = compute_risk(hourly, config=cfg, past_hours=past_hours).score
        perturbed_scores.append(score)

    min_score = min(perturbed_scores)
    max_score = max(perturbed_scores)
    score_range = round(max_score - min_score, 1)

    # Stable if perturbation range is <= 12.0 pts
    status = "stable" if score_range <= 12.0 else "borderline"

    return {
        "status": status,
        "base_score": base_score,
        "min_score": min_score,
        "max_score": max_score,
        "range": score_range,
    }


def apply_scenario(hourly: pd.DataFrame, multiplier: float) -> pd.DataFrame:
    """Scale precipitation data by multiplier (e.g. 1.0, 1.25, 1.5) for hypothetical stress testing."""
    if hourly is None or hourly.empty:
        return pd.DataFrame(columns=["time", "precipitation", "precipitation_probability", "rain"])

    scaled = hourly.copy()
    if "precipitation" in scaled.columns:
        scaled["precipitation"] = (scaled["precipitation"] * multiplier).clip(lower=0.0).round(2)
    if "rain" in scaled.columns:
        scaled["rain"] = (scaled["rain"] * multiplier).clip(lower=0.0).round(2)
    if "precipitation_probability" in scaled.columns:
        # Probability scales mildly with multiplier up to 100%
        scaled["precipitation_probability"] = (
            scaled["precipitation_probability"] * min(1.3, max(1.0, multiplier ** 0.5))
        ).clip(lower=0.0, upper=100.0).round(1)

    return scaled
