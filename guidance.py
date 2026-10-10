"""Preparedness guidance, checklists, verified official links, and WhatsApp brief generator.

Provides tiered preparedness recommendations in English and simple Tamil (needing native review),
emergency checklist items, verified disaster authority links, and copy/export-ready briefs.
Contains NO evacuation orders (readiness and decision-support only).
"""

from __future__ import annotations

from typing import Dict, List, Any
from models import ForecastData, RiskResult
from config import PERSISTENT_DISCLAIMER
from localization import category_label, translate

# Tiered Recommendations (Information and Readiness only)
TIERED_RECOMMENDATIONS: Dict[str, Dict[str, List[str]]] = {
    "Low": {
        "en": [
            "Maintain standard vigilance and check daily local weather forecasts.",
            "Ensure household rainwater spouts and street-facing grates are clear of leaves.",
            "Keep rain gear and umbrellas readily accessible.",
        ],
        "ta": [
            "வழக்கமான விழிப்புணர்வுடன் இருங்கள்; தினசரி வானிலை தகவல்களை கவனிக்கவும்.",
            "வீட்டு மழைநீர் வடிகால்களில் அடைப்புகள் இல்லாமல் பார்த்துக் கொள்ளவும்.",
            "குடைகள் மற்றும் மழை ஆடைகளை தயாராக வைத்திருக்கவும்.",
        ],
    },
    "Moderate": {
        "en": [
            "Regularly monitor local municipal and IMD weather updates.",
            "Clear rooftop drains and inspection chambers to prevent localized ponding.",
            "Fully recharge mobile phones, power banks, and rechargeable emergency lamps.",
            "Park two-wheelers and cars away from known roadside dips and low-lying hollows.",
            "Keep basic non-perishable groceries and drinking water replenished.",
        ],
        "ta": [
            "உள்ளூர் வானிலை மற்றும் மாநகராட்சி அறிவிப்புகளை தொடர்ந்து கவனிக்கவும்.",
            "கூரை மற்றும் தரை வடிகால்களை சுத்தம் செய்து நீர் தேங்குவதை தவிர்க்கவும்.",
            "கைபேசிகள், பவர் பேங்க் மற்றும் அவசர விளக்குகளை முழுமையாக மின்னேற்றம் செய்யவும்.",
            "வாகனங்களை தாழ்வான பகுதிகளில் நிறுத்தாமல் சற்று மேடான இடங்களில் நிறுத்தவும்.",
            "குடிநீர் மற்றும் அத்தியாவசிய பொருட்களை கையிருப்பில் வைக்கவும்.",
        ],
    },
    "High": {
        "en": [
            "Review household emergency supplies: drinking water (3 days), dry food, and first-aid kit.",
            "Store identity cards, property papers, and medications in sealed waterproof bags.",
            "Identify safe pedestrian and vehicular routes to elevated ground; avoid subways.",
            "Check on elderly neighbors, persons with disabilities, and young children.",
            "Charge all communications equipment and preserve mobile battery.",
            "Avoid non-essential transit or parking along storm canals during peak rainfall windows.",
        ],
        "ta": [
            "அத்தியாவசிய அவசரப் பொருட்களை சரிபார்க்கவும்: 3 நாட்களுக்கான குடிநீர், உலர் உணவு, முதலுதவி பெட்டி.",
            "அடையாள அட்டைகள் மற்றும் முக்கிய ஆவணங்களை நீர்ப்புகா பைகளில் பத்திரப்படுத்தவும்.",
            "மேடான பாதுகாப்பான இடங்களுக்கான வழிகளை முன்கூட்டியே திட்டமிடுங்கள்; சுரங்கப்பாதைகளை தவிர்க்கவும்.",
            "முதியவர்கள், மாற்றுத்திறனாளிகள் மற்றும் குழந்தைகளின் பாதுகாப்பை உறுதி செய்யவும்.",
            "தொடர்பு சாதனங்களை தயார் நிலையில் வைத்து மின்சாரத்தை சிக்கனமாக பயன்படுத்தவும்.",
            "மழை தீவிரமாக இருக்கும் நேரங்களில் தேவையற்ற பயணங்களை கண்டிப்பாக தவிர்க்கவும்.",
        ],
    },
    "Severe": {
        "en": [
            "Stay tuned strictly to official updates from IMD and State Disaster Management Authorities.",
            "Keep emergency battery torches, spare cells, and battery-operated radios on hand.",
            "Note emergency helpline numbers: State Disaster Control 1070, District Control 1077.",
            "Secure loose rooftop sheets, outdoor furniture, and potential wind/rain hazards.",
            "Do NOT attempt to cross, walk, or drive through flowing water or flooded underpasses.",
            "Stay indoors in structurally sound premises; disconnect non-critical heavy appliances.",
        ],
        "ta": [
            "IMD மற்றும் மாநில பேரிடர் மேலாண்மை ஆணையத்தின் அதிகாரப்பூர்வ அறிவிப்புகளை மட்டுமே பின்பற்றவும்.",
            "டார்ச் விளக்கு, கூடுதல் பேட்டரிகள் மற்றும் வானொலிப் பெட்டியை கைவசம் வைக்கவும்.",
            "அவசர உதவி எண்களை தயாராக வைக்கவும்: மாநில உதவி 1070, மாவட்ட உதவி 1077.",
            "கூரை மற்றும் பால்கனிகளில் உள்ள தளர்வான பொருட்களை பாதுகாப்பாக கட்டவும்.",
            "தேங்கிய அல்லது வேகமாக ஓடும் மழைநீரில் ஒருபோதும் நடக்கவோ வாகனத்தில் செல்லவோ வேண்டாம்.",
            "பாதுகாப்பான கட்டிடங்களுக்குள் இருங்கள்; தேவையற்ற மின்சாதனங்களை அணைத்து வைக்கவும்.",
        ],
    },
}

# Standard Emergency Checklist Items
CHECKLIST_ITEMS: List[Dict[str, str]] = [
    {
        "id": "kit",
        "category": "Household Kit",
        "item_en": "Potable drinking water (3-4 liters per person per day) and ready-to-eat dry rations",
        "item_ta": "குடிநீர் (நபருக்கு ஒரு நாளைக்கு 3-4 லிட்டர்) மற்றும் உலர் உணவுப் பொருட்கள்",
    },
    {
        "id": "docs",
        "category": "Documents",
        "item_en": "Identification cards, medical prescriptions, and insurance papers in zip-sealed waterproof covers",
        "item_ta": "அடையாள அட்டை, மருத்துவ ஆவணங்கள் நீர்ப்புகா பிளாஸ்டிக் உறைகளில் பத்திரப்படுத்துதல்",
    },
    {
        "id": "power",
        "category": "Power & Tech",
        "item_en": "Fully charged battery power banks, battery-powered LED torch, and spare batteries",
        "item_ta": "முழுமையாக மின்னேற்றம் செய்யப்பட்ட பவர் பேங்க், பேட்டரி டார்ச் விளக்கு மற்றும் கூடுதல் பேட்டரிகள்",
    },
    {
        "id": "vulnerable",
        "category": "Family Care",
        "item_en": "7-day supply of critical chronic medications, infant nutrition, and pet care supplies",
        "item_ta": "முதியோர்களுக்கான அத்தியாவசிய மருந்துகள், குழந்தைகள் மற்றும் செல்லப்பிராணிகளுக்கான உணவு",
    },
    {
        "id": "routes",
        "category": "Route Awareness",
        "item_en": "Awareness of designated local relief shelters and flood-free access routes",
        "item_ta": "அருகிலுள்ள நிவாரண முகாம்கள் மற்றும் வெள்ளமில்லா மேடான பாதைகளை தெரிந்து வைத்திருத்தல்",
    },
]

# Verified Official Emergency Links
VERIFIED_OFFICIAL_LINKS: List[Dict[str, Any]] = [
    {
        "name": "India Meteorological Department (IMD)",
        "url": "https://mausam.imd.gov.in",
        "scope": "National (India)",
        "verified": True,
        "note": "Official weather forecasts, radar imagery, and warnings",
    },
    {
        "name": "Tamil Nadu State Disaster Management Authority (TNDSMA)",
        "url": "https://tnsdma.tn.gov.in",
        "scope": "State (Tamil Nadu)",
        "verified": True,
        "note": "State-level disaster bulletins, control room advisories (Helpline 1070)",
    },
    {
        "name": "National Disaster Management Authority (NDMA India)",
        "url": "https://ndma.gov.in",
        "scope": "National (India)",
        "verified": True,
        "note": "Apex disaster guidelines, community preparedness protocols",
    },
    {
        "name": "World Meteorological Organization (WMO)",
        "url": "https://wmo.int",
        "scope": "International",
        "verified": True,
        "note": "Global meteorological standards and severe weather information",
    },
    {
        "name": "World Weather Information Service (WWIS)",
        "url": "https://worldweather.wmo.int",
        "scope": "International Pointer",
        "verified": True,
        "note": "National meteorological service directory for locations outside India",
    },
]


def get_recommendations(category: str, lang: str = "en") -> List[str]:
    """Retrieve tiered recommendations for the specified risk category and language."""
    cat = category if category in TIERED_RECOMMENDATIONS else "Low"
    language_key = "ta" if lang == "ta" else "en"
    return TIERED_RECOMMENDATIONS[cat].get(language_key, TIERED_RECOMMENDATIONS[cat]["en"])


def build_brief(forecast: ForecastData, risk: RiskResult, lang: str = "en") -> str:
    """Generate a compact, WhatsApp-ready text summary of the forecast and risk indicator."""
    is_synthetic = forecast.source == "synthetic"
    source_label = (
        translate("brief.synthetic_source", lang)
        if is_synthetic
        else translate("brief.forecast_source", lang, source=forecast.source.upper())
    )

    loc_name = f"{forecast.location.name}, {forecast.location.admin1}"
    coords = f"({forecast.location.latitude:.2f}°N, {forecast.location.longitude:.2f}°E)"

    # Compute 72h total from hourly forecast
    precip_72h = forecast.hourly["precipitation"].iloc[:72].sum() if not forecast.hourly.empty else 0.0

    lines: List[str] = []
    lines.append(translate("brief.title", lang))
    lines.append(f"{translate('brief.source', lang)} [{source_label}]")
    if is_synthetic:
        lines.append(translate("brief.synthetic_notice", lang))
    lines.append(f"{translate('brief.location', lang)} {loc_name} {coords}")
    lines.append(f"{translate('brief.fetched_at', lang)} {forecast.fetched_at_utc[:16]} UTC")
    lines.append(f"{translate('brief.risk', lang)} *{category_label(risk.category, lang).upper()}* ({risk.score:.1f}/100)")
    lines.append(f"{translate('brief.rain_72h', lang)} {precip_72h:.1f} mm")
    lines.append("")
    lines.append(translate("brief.drivers", lang))
    for d in risk.drivers[:3]:
        if lang == "ta":
            labels = {
                "24h rain accumulation": "risk.driver.rain_24h",
                "72h rain accumulation": "risk.driver.rain_72h",
                "Peak rain intensity": "risk.driver.peak_intensity",
                "Peak rain probability": "risk.driver.peak_prob",
                "Consecutive wet hours": "risk.driver.consecutive_wet_hours",
                "Recent antecedent rain": "risk.driver.recent_rain",
            }
            for english_label, translation_key in labels.items():
                if d.startswith(f"{english_label}:"):
                    d = f"{translate(translation_key, lang)}{d[len(english_label):]}"
                    break
        lines.append(f" • {d}")

    lines.append("")
    lines.append(translate("brief.actions", lang))
    recs = get_recommendations(risk.category, lang=lang)
    for r in recs[:3]:
        lines.append(f" • {r}")

    lines.append("")
    lines.append(translate("brief.contacts", lang))
    lines.append(f" • {translate('brief.state_helpline', lang)}")
    lines.append(f" • {translate('brief.imd_portal', lang)} https://mausam.imd.gov.in")
    lines.append("")
    disclaimer = PERSISTENT_DISCLAIMER if lang == "en" else translate("disclaimer.body", lang)
    lines.append(f"{translate('brief.disclaimer', lang)} {disclaimer}")

    return "\n".join(lines)
