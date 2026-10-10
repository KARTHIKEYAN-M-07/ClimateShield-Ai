from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

from models import FetchError

APP_PATH = str(Path(__file__).parent.parent / "app.py")


def test_app_loads_cleanly_with_mocked_fetch(sample_forecast_data):
    """Verify live fetch path renders cleanly with metrics and no exceptions."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    with patch("data.fetch_forecast", return_value=sample_forecast_data):
        at.run()

    # App must run without any unhandled tracebacks
    assert len(at.exception) == 0
    # Title must be rendered
    assert len(at.title) >= 1
    assert "ClimateShield AI" in at.title[0].value
    # Mandatory disclaimer must appear in info box
    assert any("MANDATORY ADVISORY" in info.value for info in at.info)


def test_app_failure_path_shows_friendly_message_no_traceback():
    """Verify failure path shows friendly error UI without raising unhandled exceptions."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    simulated_err = FetchError("offline", "Simulated connection loss")

    with patch("data.fetch_forecast", side_effect=simulated_err):
        with patch("data.get_last_cached_forecast", return_value=None):
            at.run()

    # Zero unhandled exceptions
    assert len(at.exception) == 0
    # Error message must be displayed to user
    assert len(at.error) >= 1
    assert "Unable to fetch live weather data" in at.error[0].value
    assert "Simulated connection loss" in at.error[0].value


def test_app_synthetic_mode_shows_synthetic_badge():
    """Verify selecting synthetic demo mode displays the prominent SYNTHETIC badge."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()

    # Find and toggle the Synthetic Demo checkbox (or set session state)
    at.session_state["use_synthetic"] = True
    at.run()

    assert len(at.exception) == 0
    # Warning or status badge must declare SYNTHETIC DEMO
    all_warnings = [w.value for w in at.warning]
    assert any("SYNTHETIC DEMO" in text for text in all_warnings)


def test_app_language_switch():
    """Verify language state toggle operates without exceptions."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.session_state["lang"] = "ta"
    at.run()

    assert len(at.exception) == 0


def test_app_language_switch_renders_tamil_and_persists():
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.session_state["use_synthetic"] = True
    at.run()
    assert len(at.exception) == 0
    assert at.session_state["lang"] == "en"
    assert at.sidebar.radio[0].value == "en"

    at.sidebar.radio[0].set_value("ta").run()

    assert len(at.exception) == 0
    assert at.session_state["lang"] == "ta"
    assert at.sidebar.radio[0].value == "ta"
    assert any("மழைப்பொழிவு" in heading.value for heading in at.subheader)
    assert "மொழி" in at.sidebar.radio[0].label
