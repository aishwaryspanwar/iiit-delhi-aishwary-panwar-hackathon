from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "src" / "app" / "dashboard.py"
SOURCE_DIRS = [Path(__file__).resolve().parents[1] / "src"]


def test_dashboard_renders_without_exceptions():
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    assert not app.exception
    assert any("Signal feed" in t.label for t in app.tabs)


def test_no_unsafe_html_in_app():
    for directory in SOURCE_DIRS:
        for path in directory.rglob("*.py"):
            assert "unsafe_allow_html" not in path.read_text(encoding="utf-8"), path


def test_try_headline_scores_and_previews_stress():
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    picker = next(s for s in app.selectbox if s.label.startswith("Start from an example"))
    picker.select("Russia launches full-scale invasion of Ukraine as explosions heard in Kyiv").run()
    assert not app.exception
    labels = {m.label: m.value for m in app.metric}
    assert labels["Event class"] == "Geopolitical"
    next(s for s in app.slider if s.label.startswith("Distinct news outlets")).set_value(25).run()
    next(s for s in app.select_slider if s.label.startswith("Mentions vs")).set_value(8.0).run()
    assert not app.exception
    labels = {m.label: m.value for m in app.metric}
    assert labels["Stress P&L (preview)"].startswith("−$")
