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
