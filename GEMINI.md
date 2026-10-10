# ClimateShield AI: Always-On Rules

1. **No ML model, training data, accuracy, or validation metrics.** The score is a transparent rule-based heuristic.
2. **Never call the score "flood probability" or "flood prediction".** Its official name is **"Rainfall Risk Indicator" (Low / Moderate / High / Severe)**.
3. **Synthetic data is user-triggered only, never silent, never mixed with live data**, and must be explicitly labeled in the banner, chart titles, and export filenames.
4. **Persistent disclaimer:** Prototype, not validated, not an official warning; follow IMD and state disaster authorities.
5. **State what the score ignores:** Terrain, drainage, soil saturation, river levels, tides, reservoir releases, local infrastructure.
6. **No auth, database, Docker, or extra infrastructure.**
7. **Never claim a test passed or a command ran unless you saw the output.**
8. **If a gate fails 3 times, stop and report the exact error.**
