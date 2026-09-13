"""Streamlit pages run without exceptions and the build page builds the fixture data."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

UI = Path(__file__).parent.parent / "manager" / "ui"
PAGES = sorted(p.name for p in (UI / "pages").glob("*.py") if p.name != "__init__.py")


@pytest.fixture
def ui_env(data, tmp_path, monkeypatch):
    """Point DATA_DIR at a copy of the fixture data before any page runs."""
    monkeypatch.setenv("DATA_DIR", str(data))
    return data


@pytest.mark.parametrize("page", PAGES)
def test_page_runs(page, ui_env):
    at = AppTest.from_file(str(UI / "pages" / page), default_timeout=10).run()
    assert not at.exception, at.exception
    assert at.title


def test_app_shell_runs(ui_env):
    at = AppTest.from_file(str(UI / "app.py"), default_timeout=10).run()
    assert not at.exception, at.exception
    assert at.sidebar.title[0].value == "Napa ja piirit"


def test_build_button_builds_fixture(ui_env, tmp_path, monkeypatch):
    monkeypatch.setattr("manager.settings.ROOT", tmp_path)  # dist/ goes to tmp, not the repo
    at = AppTest.from_file(str(UI / "pages" / "build_publish.py"), default_timeout=10).run()
    at.button(key="build").click().run()
    assert not at.exception, at.exception
    assert [m.label for m in at.metric] == ["Reittejä", "Ensikäynti", "Varoituksia"]
    assert at.metric[0].value == "1"
    assert (tmp_path / "dist" / "catalog.json").is_file()
    assert [m.value for m in at.markdown if m.value.startswith(("\u2713", "!"))] == [
        "\u2713 Skeema",
        "\u2713 Linkit",
        "\u2713 Viittaukset",
        "\u2713 K\u00e4\u00e4nn\u00f6kset",
        "\u2713 Avainvuodot",
    ]
