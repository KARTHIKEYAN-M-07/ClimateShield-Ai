# 🛡️ ClimateShield AI

> **Explainable Rainfall Risk Indicator & Preparedness Decision-Support Platform**  
> *Built for district officials, disaster responders, and communities in Tamil Nadu and beyond.*

---

## ⚠️ Mandatory Honesty Statement & Disclaimer

**PROTOTYPE ONLY**: ClimateShield AI computes a transparent, rule-based **Rainfall Risk Indicator** (Low, Moderate, High, Severe).  
- It is **NOT** a flood prediction system, flood forecast, or flood probability calculator.  
- It uses **NO machine learning models, training data, accuracy scores, or validation metrics**.  
- It has **NOT been officially validated** against hydrological models.  
- Always follow official advisories issued by the **India Meteorological Department (IMD)** and **State Disaster Management Authorities (SDMA)**.

### 🚫 What This Indicator Ignores
The score reflects purely atmospheric precipitation volume and intensity. It **does not model surface hydrology** and explicitly ignores:
1. **Terrain contours, elevation gradients, and low-lying hollows**
2. **Drainage system capacity, storm drain blockages, and maintenance**
3. **Soil saturation, antecedent moisture absorption, and percolation rates**
4. **River basin levels, upstream catchment runoff, and canal discharge**
5. **Coastal storm tides, storm surges, and estuarine backwater effects**
6. **Dam, reservoir, and lake emergency floodgate operations**
7. **Local civil infrastructure failure (culvert breaks, pumping station outages)**

---

## 🎯 Problem Statement & Who It Helps

### The Problem
During heavy northeast monsoon depressions and cyclonic storms in Tamil Nadu (e.g., Chennai 2015, Cyclone Michaung 2023), raw precipitation forecasts (`"75 mm expected"`) are difficult for non-meteorologists to interpret rapidly. Responders need actionable clarity: *Is this rain dangerous? Why is it rated that way? What should we do right now?*

### Who It Helps
- **District Officials & Ward Responders**: Get immediate 10-second situational awareness across 72 hours, identifying the heaviest 6-hour rainfall window.
- **NGO Coordinators & Volunteer Teams**: Generate WhatsApp-ready bilingual situation briefs in English and Tamil for grassroots distribution.
- **Local Residents**: Review simple, non-alarmist household preparedness checklists and access verified emergency contact hotlines (State: **1070**, District: **1077**).

---

## ⚙️ How the Heuristic Works (No ML)

The **Rainfall Risk Indicator** is computed via a transparent, deterministic mathematical heuristic:

$$\text{Score} = \sum_{i} \left( \min\left(1.0, \frac{\text{Factor}_i}{\text{Threshold}_i}\right) \times \frac{\text{Weight}_i}{\sum \text{Active Weights}} \right) \times 100$$

### Default Thresholds & Weights (`DEFAULT_CONFIG`)

| Factor | Description | Default Threshold | Default Weight | IMD / Meteorological Rationale |
| :--- | :--- | :---: | :---: | :--- |
| **`rain_24h`** | 24-Hour Accumulated Rainfall | 70.0 mm | 30% (0.30) | Aligns with IMD Heavy Rain classification (> 64.5 mm/day). |
| **`rain_72h`** | 72-Hour Cumulative Rainfall | 150.0 mm | 20% (0.20) | Multi-day persistent depression threshold. |
| **`peak_intensity`** | Heaviest Single-Hour Rain | 20.0 mm/h | 20% (0.20) | Cloudburst / intense convective cell marker. |
| **`peak_prob`** | Maximum Rain Probability | 85.0 % | 10% (0.10) | Forecast confidence level from numerical ensemble. |
| **`consecutive_wet_hours`** | Unbroken Wet Spell (≥1 mm/h) | 10.0 hrs | 10% (0.10) | Continuous surface runoff stress on urban storm gutters. |
| **`recent_rain`** *(Optional)* | Antecedent Rain in Past 24-48h | 40.0 mm | 10% (0.10) | Contextual indicator for existing ground wetness. |

### Risk Bands
- 🟢 **Low (0 - 24.9)**: Routine rainfall; standard maintenance and preparedness.
- 🟡 **Moderate (25 - 49.9)**: Sustained rain; clear rooftop gutters, monitor forecasts, recharge electronics.
- 🟠 **High (50 - 74.9)**: Heavy precipitation expected; safeguard vital documents, review high-ground shelter routes.
- 🔴 **Severe (75 - 100)**: Dangerous extreme precipitation spell; emergency helpline awareness (1070/1077), stay indoors, avoid moving water.

---

## 🌟 Key Features

1. **6-Tab Intuitive Dashboard**:
   - **Overview**: Risk gauge, key drivers, peak 6-hour rainfall window, and sensitivity indicator.
   - **Charts**: Dual-axis Plotly meteogram, cumulative rain curve, and hour-by-day intensity heatmap.
   - **Risk Explained**: Factor contribution decomposition, active thresholds table, and What-If scenario multiplier (1.0x, 1.25x, 1.5x).
   - **Preparedness**: Actionable bilingual recommendations, interactive household checklist, verified authority links, and exportable WhatsApp brief.
   - **Compare Districts**: Regional Tamil Nadu district ranking and tokenless Plotly map.
   - **About & Data**: Full transparency on units, fetch timestamps, data quality audit, and Open-Meteo CC BY 4.0 license attribution.
2. **Deterministic Synthetic Scenarios**:
   - Seeded simulations (`Cyclone-style heavy burst`, `Steady monsoon`, `Dry spell`) for offline drills and testing.
   - Synthetic data is **user-triggered only**, never mixed with live data, and prominently labeled across banners, charts, and exports.
3. **Resilient Failure Recovery**:
   - Exponential-backoff retries on network blips and HTTP 429/5xx.
   - In-memory fallback: Automatically offers the last successful live fetch if the network drops.
   - Graceful error cards with one-click switch to Synthetic Demo Mode (no tracebacks).
4. **Bilingual Support**:
   - Toggle between English and simple Tamil (தமிழ்).
   - *Note*: Tamil translations are provided for community accessibility and flagged for native-speaker meteorological review.

---

## 🚀 Quickstart & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- No database, Docker, or API keys required!

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/<your-username>/climateshield-ai.git
cd climateshield-ai

python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
```

### 2. Install Pinned Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Automated Test Suite
```bash
pytest -v
```
*(All 56 unit, integration, and UI tests pass in ~1.5s.)*

### 4. Launch the Streamlit App
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## ⏱️ 60-Second Judge Demo Script

1. **[0:00 - 0:10] Introduction & Honesty Anchor**:
   > *"Judges, ClimateShield AI is a transparent decision-support tool turning raw Open-Meteo forecasts into an explainable Rainfall Risk Indicator. Notice our persistent banner: This is rule-based heuristics, NOT flood prediction, and uses zero ML black-boxes."*
2. **[0:10 - 0:25] Live Situational Awareness (Overview & Charts)**:
   > *"In 10 seconds, a district collector in Chennai sees the score, the top meteorological drivers, and the exact 6-hour peak rainfall window. The Charts tab breaks down hourly intensity alongside cumulative 24h, 48h, and 72h markers."*
3. **[0:25 - 0:40] Transparency, Sensitivity & What-If**:
   > *"In 'Risk Explained', every single point is attributed to a physical factor. Move the What-If slider to 1.5x to stress-test how a 50% heavier burst would shift the district into Severe risk."*
4. **[0:40 - 0:50] Bilingual Preparedness & WhatsApp Brief**:
   > *"Switch the language toggle to Tamil. The Preparedness tab gives responders an interactive checklist and an instant, copy-ready WhatsApp alert formatted with official emergency numbers (1070 / 1077) and mandatory disclaimers."*
5. **[0:50 - 1:00] Offline Fallback & Synthetic Mode**:
   > *"If the internet cuts out during a cyclone, ClimateShield never crashes with a traceback. It falls back to cached data or allows instant switching to seeded Synthetic Demo Mode, which clearly labels all outputs with '[SYNTHETIC DEMO]'."*

---

## ❓ Judge Q&A

### Q1: Is this a flood prediction model?
**Answer**: Absolutely not. Flood forecasting requires hydraulic modeling of river cross-sections, digital elevation models (DEM), soil percolation, stormwater pipe capacity, and tidal storm surges. ClimateShield AI is strictly a **Rainfall Risk Indicator** measuring atmospheric rain hazard for early decision-support and preparedness.

### Q2: How accurate is the indicator?
**Answer**: Because this is a transparent rule-based heuristic rather than a predictive machine learning model, accuracy metrics (like RMSE or AUC-ROC) do not apply. Its value lies in transparency, explainability, and standardized translation of meteorological volume into operational preparedness tiers.

### Q3: Why were these specific thresholds and weights chosen?
**Answer**: Defaults are grounded in meteorological thresholds used by the India Meteorological Department (e.g., >64.5 mm/day as heavy rain) and empirical monsoon intensities. Importantly, all thresholds and weights are fully configurable via the sidebar so local authorities can calibrate them for different regional topographies.

### Q4: What is on the future roadmap?
**Answer**:
1. Calibrate threshold baselines against IMD historical station observation data.
2. Integrate open-source elevation contour data (Copernicus DEM) to highlight local terrain hollows.
3. Incorporate soil moisture saturation data (NASA SMAP / ECMWF ERA5-Land).
4. Validate operational guidance in partnership with disaster management researchers and native Tamil domain translators.

---

## 📜 Attribution & Data License

- Weather forecasts powered by the [Open-Meteo Weather API](https://open-meteo.com/).
- Weather data provided under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
