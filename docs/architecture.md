# ClimateShield AI Architecture

ClimateShield AI is a streamlined, transparent decision-support system converting Open-Meteo precipitation forecasts into an explainable **Rainfall Risk Indicator** paired with actionable preparedness guidance.

```mermaid
flowchart TD
    subgraph UI ["User Interface Layer (Streamlit app.py)"]
        UI_Header["Status Banner & Mandatory Disclaimer"]
        UI_Sidebar["Presets / Search / Sliders / Synthetic Toggle"]
        UI_Tabs["6 Tabs: Overview | Charts | Risk Explained | Preparedness | Compare | About"]
    end

    subgraph DataLayer ["Data & Ingestion Layer (data.py / synthetic.py)"]
        OM_Geo["Open-Meteo Geocoding API"]
        OM_Fc["Open-Meteo Forecast API"]
        TTL_Cache[("In-Memory TTL Cache (5 min)")]
        Fallback_Cache[("Last Successful Response Cache")]
        Synth_Gen["Seeded Synthetic Generator (synthetic.py)"]
    end

    subgraph RiskEngine ["Rule-Based Heuristic Engine (risk.py)"]
        Raw_Factors["Factor Extractor (24h, 72h, Peak Intensity, Probability, Wet Hours)"]
        Norm_Engine["Threshold Normalization & Config Weights (config.py)"]
        Peak_Win["Rolling 6h Heaviest Window Finder"]
        Sensitivity_Test["Sensitivity Perturbation Analysis (+/-20%)"]
        Scenario_Scale["Hypothetical Stress Test Scaler (1.0x, 1.25x, 1.5x)"]
    end

    subgraph OutputLayer ["Presentation & Action Components"]
        Plotly_Charts["Plotly Visualizations (charts.py)"]
        Guidance_Recs["Tiered Bilingual Guidance & Brief (guidance.py)"]
        Official_Links["Verified Official Authorities (IMD / SDMA / NDMA / WMO)"]
    end

    UI_Sidebar -->|User Query| OM_Geo
    UI_Sidebar -->|Location Selection| OM_Fc
    OM_Fc -->|Success| TTL_Cache
    TTL_Cache --> Fallback_Cache
    OM_Fc -.->|Failure: 429/5xx/Offline| Fallback_Cache
    UI_Sidebar -->|User-Triggered Toggle| Synth_Gen

    TTL_Cache -->|ForecastData (Live/Cached)| Raw_Factors
    Fallback_Cache -.->|Fallback ForecastData| Raw_Factors
    Synth_Gen -->|ForecastData (Synthetic)| Raw_Factors

    Raw_Factors --> Norm_Engine
    Raw_Factors --> Peak_Win
    Norm_Engine --> Sensitivity_Test
    Raw_Factors --> Scenario_Scale

    Norm_Engine -->|RiskResult| Plotly_Charts
    Norm_Engine -->|RiskResult| Guidance_Recs
    Guidance_Recs --> Official_Links

    Plotly_Charts --> UI_Tabs
    Guidance_Recs --> UI_Tabs
```

---

## Component Separation of Concerns

1. **`models.py` (Contracts)**:
   Immutable dataclasses (`Location`, `ForecastData`, `DataQuality`, `RiskConfig`, `RiskResult`, `FetchError`). Strictly no UI logic.
2. **`config.py` (Configuration)**:
   Authoritative defaults (`DEFAULT_CONFIG`), Tamil Nadu district coordinates, risk thresholds, persistent disclaimers, and physical omissions.
3. **`data.py` (Data Access)**:
   Network client with exponential backoff, rate limit recovery, dynamic unit parsing, and in-memory fallback. All exceptions mapped to `FetchError`.
4. **`risk.py` (Domain Logic)**:
   Pure functions with zero external dependencies. Computes transparent 0–100 heuristic score, factor contributions, top drivers, peak 6-hour windows, and stability classifications.
5. **`synthetic.py` (Offline Scenarios)**:
   Deterministic seeded scenarios (`Cyclone-style heavy burst`, `Steady monsoon`, `Dry spell`). Always isolated and tagged `source="synthetic"`.
6. **`guidance.py` (Preparedness & Communication)**:
   Bilingual actionable checklists and WhatsApp-ready brief builder.
7. **`charts.py` (Visualizations)**:
   Plotly figures with automatic `[SYNTHETIC DEMO]` labeling and resilient empty-data handling.
8. **`app.py` (Presentation)**:
   Thin Streamlit frontend with 6 interactive tabs and graceful failure recovery.

---

## Rendering Architecture Diagram

To render this diagram to PNG using the Mermaid CLI:
```bash
npx @mermaid-js/mermaid-cli -i docs/architecture.md -o docs/architecture.png
```
Or view the generated vector asset: `docs/architecture.svg`.
