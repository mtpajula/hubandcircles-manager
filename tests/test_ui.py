"""Streamlit pages run without exceptions and the build page builds the fixture data."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from manager.ui import texts
from manager.validate import CHECKS

UI = Path(__file__).parent.parent / "manager" / "ui"
PAGES = sorted(p.name for p in (UI / "views").glob("*.py") if p.name != "__init__.py")


@pytest.fixture
def ui_env(data, tmp_path, monkeypatch):
    """Point DATA_DIR at a copy of the fixture data before any page runs."""
    monkeypatch.setenv("DATA_DIR", str(data))
    return data


@pytest.mark.parametrize("page", PAGES)
def test_page_runs(page, ui_env):
    at = AppTest.from_file(str(UI / "views" / page), default_timeout=10).run()
    assert not at.exception, at.exception
    assert at.title


def test_app_shell_runs(ui_env):
    at = AppTest.from_file(str(UI / "app.py"), default_timeout=10).run()
    assert not at.exception, at.exception
    assert at.sidebar.title[0].value == "Napa ja piirit"


@pytest.fixture
def build_page(ui_env, tmp_path, monkeypatch):
    """The build page with dist/ and .state.json under tmp, not the repo."""
    import manager.build  # noqa: F401 – bind ROOT-based defaults (.env.example) before patching

    monkeypatch.setattr("manager.settings.ROOT", tmp_path)
    monkeypatch.setattr("manager.state.STATE_FILE", tmp_path / ".state.json")
    return AppTest.from_file(str(UI / "views" / "build_publish.py"), default_timeout=10)


def test_build_page_shows_three_steps(build_page):
    at = build_page.run()
    assert not at.exception, at.exception
    assert [h.value for h in at.subheader] == ["1 · Build", "2 · Esikatselu", "3 · Julkaise"]
    assert [b.label for b in at.button] == ["Aja build", "Käynnistä esikatselu", "Julkaise"]


def test_build_button_builds_fixture(build_page, tmp_path):
    at = build_page.run()
    assert not at.metric
    at.button(key="build").click().run()
    assert not at.exception, at.exception
    assert [m.label for m in at.metric] == ["Reittejä", "Ensikäynti", "Varoituksia"]
    assert at.metric[0].value == "1"
    assert (tmp_path / "dist" / "catalog.json").is_file()
    assert (tmp_path / ".state.json").is_file()
    # Every check of table 7.2 that exists, in its order (texts.CHECK_NAMES follows CHECKS).
    assert [m.value for m in at.markdown if m.value.startswith(("\u2713", "!", "i "))] == [
        f"\u2713 {texts.CHECK_NAMES[check]}" for check in CHECKS
    ]


def test_publish_button_waits_for_a_fresh_build(build_page, ui_env, frontend):
    # Relative paths: an absolute one would repeat DATA_DIR, which the secrets check rejects.
    (ui_env / "publish.json").write_text(
        json.dumps(
            {
                "frontend": {"path": "../frontend"},
                "targets": [{"id": "local", "type": "directory", "path": "../out"}],
                "headers": [],
            }
        )
    )
    at = build_page.run()
    assert not at.exception, at.exception
    assert at.checkbox(key="target_local").label == "local · directory · ../out"
    assert f"Frontend: {frontend}" in [c.value for c in at.caption]
    assert at.button(key="publish").disabled and at.button(key="preview_start").disabled
    assert [c.value for c in at.caption if c.value == "Aja build ensin"] == ["Aja build ensin"] * 2

    at.button(key="build").click().run()
    assert not at.exception, at.exception
    assert not at.button(key="publish").disabled and not at.button(key="preview_start").disabled
    assert not [c for c in at.caption if c.value == "Aja build ensin"]


def test_routes_page_form_metrics_and_table(ui_env):
    at = AppTest.from_file(str(UI / "views" / "routes.py"), default_timeout=10).run()
    assert not at.exception, at.exception
    assert at.selectbox(key="route_select").value == "__new__"
    assert at.text_input(key="route_id").value == ""
    assert [b.label for b in at.button if b.label.startswith(("Tallenna", "Poista"))] == [
        "Tallenna reitti",
        "Poista reitti",
    ]
    assert len(at.dataframe) == 1 and len(at.dataframe[0].value) == 1
    assert list(at.dataframe[0].value.iloc[0])[:3] == ["Testilenkki", "Gravel", "fi, en"]
    assert not at.metric  # nothing selected yet

    at.selectbox(key="route_select").select("test-loop").run()
    assert not at.exception, at.exception
    assert at.text_input(key="name_fi_test-loop").value == "Testilenkki"
    assert at.text_area(key="desc_en_test-loop").value == "A short test route."
    assert [(m.label, m.value) for m in at.metric] == [
        ("Pituus", "1,3 km"),
        ("Nousu", "29 m"),
        ("Kuvia", "0"),
    ]


def test_routes_page_saves_and_deletes(ui_env):
    at = AppTest.from_file(str(UI / "views" / "routes.py"), default_timeout=10).run()
    at.selectbox(key="route_select").select("test-loop").run()
    at.text_input(key="name_fi_test-loop").set_value("Muokattu lenkki")
    at.selectbox(key="maintainer_test-loop").select("municipal")
    at.number_input(key="lipas_id_test-loop").set_value(613791)
    at.button(key="FormSubmitter:route_form-Tallenna reitti").click().run()
    assert not at.exception, at.exception
    assert at.success[0].value.startswith("Reitti tallennettu")
    card = json.loads((ui_env / "routes" / "test-loop" / "route.json").read_text())
    assert card["name"]["fi"] == "Muokattu lenkki"
    assert card["maintainer"] == "municipal" and card["lipas_id"] == 613791
    assert card["sections"][0]["content"]["en"] == "A short test route."  # untouched
    assert list(at.dataframe[0].value.iloc[0])[3] == "kunta"

    at.button(key="FormSubmitter:route_form-Poista reitti").click().run()
    assert at.warning[0].value.startswith("Rastita")  # unconfirmed: nothing deleted
    assert (ui_env / "routes" / "test-loop").is_dir()
    at.checkbox(key="confirm_delete_test-loop").check()
    at.button(key="FormSubmitter:route_form-Poista reitti").click().run()
    assert not at.exception, at.exception
    assert at.success[0].value == "Reitti poistettu: test-loop"
    assert not (ui_env / "routes" / "test-loop").exists()
    assert at.selectbox(key="route_select").value == "__new__"


def test_themes_page_saves_theme_and_project(ui_env):
    at = AppTest.from_file(str(UI / "views" / "themes.py"), default_timeout=10).run()
    assert not at.exception, at.exception
    assert [e.label for e in at.expander][:2] == [
        "Talvimaasto · järjestys 1",
        "Maasto · järjestys 2",
    ]
    assert at.caption[1].value == "Kontrasti valkoista tekstiä vasten 6,6:1"
    assert not at.warning

    at.color_picker(key="primary_gravel").set_value("#cccccc")
    at.number_input(key="order_gravel").set_value(7)
    at.button(key="save_theme_gravel").click().run()
    assert not at.exception, at.exception
    assert any(w.value.startswith("Kontrasti alle") for w in at.warning)
    theme = json.loads((ui_env / "themes" / "gravel.json").read_text())
    assert theme["order"] == 7 and theme["colors"]["primary"] == "#cccccc"

    at.checkbox(key="itrs_exposure_locked").check()
    at.number_input(key="itrs_exposure").set_value(4)
    at.text_input(key="github_repo").set_value("org/repo")
    at.text_input(key="issue_form").set_value("route-report.yml")
    at.button(key="save_project").click().run()
    assert not at.exception, at.exception
    assert at.success[0].value.startswith("Projektiasetukset tallennettu")
    project = json.loads((ui_env / "project.json").read_text())
    assert project["itrs_scales"] == {"exposure": 4}
    assert project["feedback"] == {"github_repo": "org/repo", "issue_form": "route-report.yml"}
