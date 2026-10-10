"""Regression tests for centralized English and Tamil presentation text."""

import pytest

from charts import plot_hourly_meteogram, plot_risk_contributions
from localization import TRANSLATIONS, category_label, missing_translation_keys, translate
from risk import compute_risk


def test_translation_catalogs_have_identical_complete_keys():
    assert set(TRANSLATIONS) == {"en", "ta"}
    assert missing_translation_keys() == {"en": set(), "ta": set()}
    assert set(TRANSLATIONS["en"]) == set(TRANSLATIONS["ta"])
    intentional_tamil_labels = {"language.label", "language.tamil"}
    for key, value in TRANSLATIONS["en"].items():
        if key not in intentional_tamil_labels:
            assert not any("\u0b80" <= char <= "\u0bff" for char in value), key


def test_missing_translation_key_fails_loudly():
    with pytest.raises(KeyError, match="Missing 'ta' translation"):
        translate("not.a.real.translation", "ta")


def test_language_switch_only_changes_risk_presentation(sample_forecast_data):
    english = compute_risk(sample_forecast_data.hourly, lang="en")
    tamil = compute_risk(sample_forecast_data.hourly, lang="ta")

    assert tamil.score == english.score
    assert tamil.contributions == english.contributions
    assert tamil.category == english.category
    assert category_label(tamil.category, "ta") != tamil.category
    assert any("\u0b80" <= char <= "\u0bff" for char in tamil.explanation)
    assert any("\u0b80" <= char <= "\u0bff" for char in tamil.drivers[0])


def test_charts_translate_labels_without_changing_values(sample_forecast_data):
    english = plot_hourly_meteogram(sample_forecast_data, lang="en")
    tamil = plot_hourly_meteogram(sample_forecast_data, lang="ta")
    assert english.layout.title.text != tamil.layout.title.text
    assert english.layout.xaxis.title.text != tamil.layout.xaxis.title.text
    assert list(english.data[0].y) == list(tamil.data[0].y)
    assert english.data[0].name != tamil.data[0].name

    risk = compute_risk(sample_forecast_data.hourly)
    contributions_en = plot_risk_contributions(risk, lang="en")
    contributions_ta = plot_risk_contributions(risk, lang="ta")
    assert list(contributions_en.data[0].x) == list(contributions_ta.data[0].x)
    assert list(contributions_en.data[0].y) != list(contributions_ta.data[0].y)
