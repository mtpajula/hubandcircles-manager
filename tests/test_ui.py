"""Streamlit pages run without exceptions and the build page builds the fixture data."""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from manager import store
from manager.sources import osm
from manager.ui import texts
from manager.validate import CHECKS

from .conftest import write_jpeg

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
    # Presentation coverage per theme (7.2, report): the fixture route is in gravel only.
    assert "**Esitystavan kattavuus teemoittain**" in [m.value for m in at.markdown]
    table = at.dataframe[0].value
    assert list(table.columns) == ["teema", "kohta", "tieto", "reittejä"]
    rows = {(r["teema"], r["kohta"], r["tieto"]): r["reittejä"] for _, r in table.iterrows()}
    assert rows[("gravel", "avainluku", "pintaosuudet")] == "1 / 1 reittiä"
    assert rows[("gravel", "avainluku", "ITRS kestävyys")] == "1 / 1 reittiä"
    assert rows[("gravel", "nauha", "pinta")] == "1 / 1 reittiä"
    assert rows[("mtb", "nauha", "ITRS tekninen")] == "0 / 0 reittiä"


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
    at.button(key="FormSubmitter:route_form-Tallenna reitti").click().run()
    assert not at.exception, at.exception
    assert at.success[0].value.startswith("Reitti tallennettu")
    card = json.loads((ui_env / "routes" / "test-loop" / "route.json").read_text())
    assert card["name"]["fi"] == "Muokattu lenkki"
    assert card["sections"][0]["content"]["en"] == "A short test route."  # untouched

    at.button(key="FormSubmitter:route_form-Poista reitti").click().run()
    assert at.warning[0].value.startswith("Rastita")  # unconfirmed: nothing deleted
    assert (ui_env / "routes" / "test-loop").is_dir()
    at.checkbox(key="confirm_delete_test-loop").check()
    at.button(key="FormSubmitter:route_form-Poista reitti").click().run()
    assert not at.exception, at.exception
    assert at.success[0].value == "Reitti poistettu: test-loop"
    assert not (ui_env / "routes" / "test-loop").exists()
    assert at.selectbox(key="route_select").value == "__new__"


def _route_card(ui_env) -> dict:
    return json.loads((ui_env / "routes" / "test-loop" / "route.json").read_text())


@pytest.fixture
def routes_page(ui_env):
    at = AppTest.from_file(str(UI / "views" / "routes.py"), default_timeout=10).run()
    at.selectbox(key="route_select").select("test-loop").run()
    assert not at.exception, at.exception
    return at


def test_routes_page_shows_the_five_sections(routes_page):
    at = routes_page
    assert [e.label for e in at.expander][:5] == [
        "Kuvat",
        "ITRS-arvio",
        "Vaativin kohta",
        "Segmenttieditori",
        "Ylläpito",
    ]
    assert "ITRS ja vaativin kohta: ei arvioitu · vaativin kohta ei valittu — muokkaa alla" in [
        c.value for c in at.caption
    ]
    # Fixture: one 1.3 km segment with surface and traffic over a 1.3 km track.
    assert "**kattavuus 100 % · 0,0 km ilman tietoa**" in [m.value for m in at.markdown]
    assert any(w.value.startswith("Asteikkoa ei ole lukittu") for w in at.warning)
    assert at.selectbox(key="itrs_endurance_test-loop").value == "blue"
    assert at.button(key="save_segments_test-loop").label == "Tallenna segmentit"
    assert not at.button(key="save_segments_test-loop").disabled


def test_routes_page_saves_itrs(routes_page, ui_env):
    at = routes_page
    assert at.text_input(key="itrs_assessed_by_test-loop").value == ""
    at.selectbox(key="itrs_technical_test-loop").select("red")
    at.number_input(key="itrs_exposure_test-loop").set_value(2)
    at.text_input(key="itrs_assessed_by_test-loop").set_value("M. Pajula")
    at.button(key="save_itrs_test-loop").click().run()
    assert not at.exception, at.exception
    assert at.success[0].value == "ITRS-arvio tallennettu."
    itrs = _route_card(ui_env)["itrs"]
    assert itrs["technical"] == "red" and itrs["endurance"] == "blue" and itrs["exposure"] == 2
    assert itrs["assessed_by"] == "M. Pajula" and "wilderness" not in itrs
    assert itrs["assessed_on"] == datetime.now(UTC).astimezone().date().isoformat()


def test_routes_page_maintenance_refuses_non_municipal_without_reason(routes_page, ui_env):
    at = routes_page
    at.selectbox(key="maintainer_test-loop").select("non_municipal").run()
    assert at.text_input(key="lipas_none_test-loop").disabled
    assert [c.label for c in at.checkbox if c.key.startswith("reason_")] == [
        "yksityistie, ei lupaa",
        "ei reittimerkintöjä",
        "ei kunnossapitoa",
        "maastoliikennelaki",
        "kausiluonteinen",
    ]
    at.button(key="save_maintenance_test-loop").click().run()
    assert not at.exception, at.exception
    assert at.error[0].value.startswith("Validointi: ylläpito on non_municipal")
    assert "maintainer" not in _route_card(ui_env)

    at.checkbox(key="reason_unmarked_test-loop").check()
    at.text_input(key="note_test-loop_fi").set_value("Merkinnät puuttuvat")
    at.button(key="save_maintenance_test-loop").click().run()
    assert not at.exception, at.exception
    card = _route_card(ui_env)
    assert card["maintainer"] == "non_municipal"
    assert card["non_municipal_reasons"] == ["unmarked"]
    assert card["maintenance_note"] == {"fi": "Merkinnät puuttuvat"}
    # The last dataframe is the routes table; the segment editor comes before it.
    assert list(at.dataframe[-1].value.iloc[0])[3] == "ei kunnan · 1 syytä"

    at.selectbox(key="maintainer_test-loop").select("municipal").run()
    at.number_input(key="lipas_id_test-loop").set_value(613791)
    at.button(key="save_maintenance_test-loop").click().run()
    card = _route_card(ui_env)
    assert card["maintainer"] == "municipal" and card["lipas_id"] == 613791
    assert "non_municipal_reasons" not in card or card["non_municipal_reasons"] == []
    assert list(at.dataframe[-1].value.iloc[0])[3] == "kunta"


def test_routes_page_hardest_section_prefills_km_from_exif(ui_env):
    directory = ui_env / "routes" / "test-loop"
    write_jpeg(directory / "media" / "rocks.jpg", (25.7050, 66.5040))
    card = _route_card(ui_env)
    card["media"] = {"media/rocks.jpg": {"author": "M. Pajula", "license": "CC BY 4.0"}}
    (directory / "route.json").write_text(json.dumps(card))
    at = AppTest.from_file(str(UI / "views" / "routes.py"), default_timeout=10).run()
    at.selectbox(key="route_select").select("test-loop").run()
    assert not at.exception, at.exception
    assert at.text_input(key="author_media/rocks.jpg_test-loop").value == "M. Pajula"
    at.selectbox(key="hardest_media_test-loop").select("media/rocks.jpg").run()
    assert not at.exception, at.exception
    km = at.number_input(key="hardest_km_media/rocks.jpg_test-loop").value
    assert km is not None and 0.0 <= km <= 1.35
    assert "Km laskettu kuvan EXIF-sijainnista projisoimalla. Voit korjata arvon." in [
        c.value for c in at.caption
    ]
    at.text_input(key="hardest_desc_test-loop_fi").set_value("Kivikko")
    at.button(key="save_hardest_test-loop").click().run()
    assert not at.exception, at.exception
    hardest = _route_card(ui_env)["hardest_section"]
    assert hardest == {"media": "media/rocks.jpg", "km": km, "description": {"fi": "Kivikko"}}

    # Removing the image drops the file and every reference to it.
    at.checkbox(key="remove_media/rocks.jpg_test-loop").check()
    at.button(key="save_images_test-loop").click().run()
    assert not at.exception, at.exception
    assert at.success[0].value == "Kuvat tallennettu: 0 kuvaa"
    card = _route_card(ui_env)
    assert "hardest_section" not in card and card.get("media", {}) == {}
    assert not (directory / "media" / "rocks.jpg").exists()


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
    assert theme["presentation"]["band"] == ["elevation", "surface"]  # untouched

    at.multiselect(key="band_gravel").set_value(
        ["elevation", "surface", "traffic", "itrs_technical"]
    )
    at.selectbox(key="hero_image_gravel").select("hardest_section")
    at.text_input(key="services_first_gravel").set_value("cafe, water")
    at.button(key="save_theme_gravel").click().run()
    assert not at.exception, at.exception
    presentation = json.loads((ui_env / "themes" / "gravel.json").read_text())["presentation"]
    assert presentation["band"] == ["elevation", "surface", "traffic", "itrs_technical"]
    assert presentation["hero_image"] == "hardest_section"
    assert presentation["service_categories_first"] == ["cafe", "water"]

    at.multiselect(key="band_gravel").set_value(
        ["surface", "traffic", "itrs_technical", "elevation"]
    )
    at.multiselect(key="key_figures_gravel").set_value(["length", "itrs_technical"])
    at.button(key="save_theme_gravel").click().run()
    assert not at.exception, at.exception
    presentation = json.loads((ui_env / "themes" / "gravel.json").read_text())["presentation"]
    assert presentation["key_figures"] == ["length", "itrs_technical"]

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


# --- Services page (ADMIN-UI-SPEC 4, OSM part) ------------------------------------------------

OSM_SAMPLE = Path(__file__).parent / "fixtures" / "osm" / "overpass_sample.json"


# --- Layers page (ADMIN-UI-SPEC section 3) ------------------------------------------------------

WMS_SAMPLE = Path(__file__).parent / "fixtures" / "wms" / "capabilities_sample.xml"


def test_layers_page_table_and_edit(ui_env):
    at = AppTest.from_file(str(UI / "views" / "layers.py"), default_timeout=10).run()
    assert not at.exception, at.exception
    table = at.dataframe[0].value
    assert list(table.columns) == ["taso", "nimi", "paikka", "muoto", "teemat", "oletus"]
    assert list(table.iloc[0]) == [
        "guide-map",
        "Opaskartta",
        "pohjakartta",
        "wms",
        "Maantie, Gravel",
        "päällä",
    ]
    assert [e.label for e in at.expander] == ["Muokkaa: Opaskartta"]
    assert at.text_input(key="wms_layers_guide-map").value == "Opaskartta_qgs"
    assert not at.checkbox(key="all_themes_guide-map").value

    at.checkbox(key="all_themes_guide-map").check()
    at.multiselect(key="routes_guide-map").set_value(["test-loop"])
    at.checkbox(key="default_on_guide-map").uncheck()
    at.number_input(key="opacity_guide-map").set_value(0.8)
    at.text_input(key="wms_layers_guide-map").set_value("Pohjakartta")
    at.button(key="save_layer_guide-map").click().run()
    assert not at.exception, at.exception
    card = json.loads((ui_env / "layers" / "guide-map.json").read_text(encoding="utf-8"))
    assert card["visible_in"] == {"themes": "*", "routes": ["test-loop"]}
    assert card["default_on"] is False and card["opacity"] == 0.8
    assert card["wms"]["layers"] == "Pohjakartta" and card["source"] == {"method": "wms_external"}
    assert list(at.dataframe[0].value.iloc[0])[4:] == ["kaikki", "pois"]

    at.button(key="delete_layer_guide-map").click().run()
    assert (ui_env / "layers" / "guide-map.json").is_file()  # not confirmed
    assert any(w.value == texts.DELETE_UNCONFIRMED for w in at.warning)
    at.checkbox(key="confirm_delete_guide-map").check()
    at.button(key="delete_layer_guide-map").click().run()
    assert not at.exception, at.exception
    assert not (ui_env / "layers" / "guide-map.json").exists()
    assert not at.dataframe and at.caption[1].value == texts.LAYERS_NONE


def test_layers_page_adds_wms_and_xyz_layers(ui_env, monkeypatch):
    seen = {}

    def fake_fetch(url, *, timeout_s=30):
        seen["url"] = url
        return WMS_SAMPLE.read_bytes()

    monkeypatch.setattr("manager.sources.wms.fetch", fake_fetch)
    at = AppTest.from_file(str(UI / "views" / "layers.py"), default_timeout=10).run()
    assert not at.exception, at.exception
    assert [b.label for b in at.button if b.key == "wms_fetch"] == ["Hae tasot palvelimelta"]
    at.button(key="wms_fetch").click().run()
    assert not at.exception, at.exception
    assert seen["url"] == "https://rovaniemi.asiointi.fi/teklaogcweb/WMS.ashx"
    assert at.selectbox(key="wms_chosen").options == [
        "Ilmakuva 2025",
        "Opaskartta_qgs",
        "Pohjakartta",
    ]
    at.selectbox(key="wms_chosen").select("Pohjakartta")
    at.text_input(key="wms_id").set_value("base-map")
    at.text_input(key="layer_name_new_wms_fi").set_value("Pohjakartta")
    at.text_input(key="layer_name_new_wms_en").set_value("Base map")
    at.checkbox(key="all_themes_new_wms").uncheck().run()  # enables the theme list
    at.multiselect(key="themes_new_wms").set_value(["mtb"])
    at.checkbox(key="default_on_new_wms").check()
    at.text_input(key="attribution_new_wms").set_value("© Rovaniemen kaupunki")
    at.button(key="save_new_wms").click().run()
    assert not at.exception, at.exception
    card = json.loads((ui_env / "layers" / "base-map.json").read_text(encoding="utf-8"))
    assert card == {
        "id": "base-map",
        "name": {"fi": "Pohjakartta", "en": "Base map"},
        "slot": "base",
        "source": {"method": "wms_external"},
        "visible_in": {"themes": ["mtb"], "routes": []},
        "default_on": True,
        "attribution": "© Rovaniemen kaupunki",
        "url": "https://rovaniemi.asiointi.fi/teklaogcweb/WMS.ashx",
        "wms": {
            "version": "1.1.1",
            "layers": "Pohjakartta",
            "format": "image/png",
            "srs": "EPSG:3857",
        },
    }

    # A taken id and a missing name are refused; then an XYZ layer with a template url.
    at.text_input(key="xyz_id").set_value("guide-map")
    at.button(key="save_new_xyz").click().run()
    assert any(e.value == texts.LAYER_NEEDS_ID_AND_NAME for e in at.error)
    at.text_input(key="layer_name_new_xyz_fi").set_value("Toner")
    at.button(key="save_new_xyz").click().run()
    assert any(e.value.startswith("Tunniste guide-map on jo") for e in at.error)
    at.text_input(key="xyz_id").set_value("toner")
    at.button(key="save_new_xyz").click().run()
    assert any(e.value.startswith("Tallennus epäonnistui") for e in at.error)  # no url
    at.text_input(key="xyz_url").set_value("https://tiles.example.org/{z}/{x}/{y}.png")
    at.text_input(key="attribution_new_xyz").set_value("© Example")
    at.button(key="save_new_xyz").click().run()
    assert not at.exception, at.exception
    card = json.loads((ui_env / "layers" / "toner.json").read_text(encoding="utf-8"))
    assert card["source"] == {"method": "xyz_external"} and card["visible_in"]["themes"] == "*"
    assert card["url"] == "https://tiles.example.org/{z}/{x}/{y}.png" and "wms" not in card
    assert list(at.dataframe[0].value["taso"]) == ["base-map", "guide-map", "toner"]


def test_services_page_with_empty_snapshot(ui_env, monkeypatch):
    monkeypatch.setenv("VF_API_KEY", "")  # empty counts as missing and shadows a real .env
    at = AppTest.from_file(str(UI / "views" / "services.py"), default_timeout=10).run()
    assert not at.exception, at.exception
    assert [h.value for h in at.subheader] == [
        "OSM",
        "Visit Finland",
        "Uusi piste",
        "Korjaa tai piilota",
        "Käsin tehdyt merkinnät",
    ]
    captions = [c.value for c in at.caption]
    assert captions.count("Ei tilannekuvaa") == 2
    assert "Ei palvelupisteitä: hae ensin tilannekuva." in captions
    assert "Ei käsin tehtyjä merkintöjä." in captions
    assert "Visit Finland -haku ei ole käytössä: VF_API_KEY puuttuu .env:stä." in captions
    assert [b.label for b in at.button] == [
        "Hae OSM:stä",
        "Hae Visit Finlandista",
        "Tallenna piste",
    ]
    assert at.button(key="visitfinland_fetch").disabled
    assert not at.metric and not at.dataframe


def test_services_page_fetch_shows_diff_and_accept_writes_snapshot(ui_env, monkeypatch):
    from manager.sources import osm

    elements = json.loads(OSM_SAMPLE.read_text(encoding="utf-8"))["elements"]
    calls = []
    monkeypatch.setattr(osm, "fetch", lambda area, **kw: calls.append(area) or elements)
    at = AppTest.from_file(str(UI / "views" / "services.py"), default_timeout=10).run()
    at.button(key="osm_fetch").click().run()
    assert not at.exception, at.exception
    assert calls == [(25.4, 66.3, 26.2, 66.7)]
    assert [(m.label, m.value) for m in at.metric] == [
        ("Uusia", "+5"),
        ("Poistuneita", "\u22120"),
        ("Muuttuneita", "0"),
        ("Yhteensä", "5"),
    ]
    table = at.dataframe[0].value
    assert list(table.columns) == ["muutos", "nimi", "kategoria", "id"]
    assert list(table["muutos"]) == ["uusi"] * 5
    assert list(table["nimi"])[:2] == ["Kahvila Napa", ""]
    assert not (ui_env / "services" / "osm.geojson").exists()  # nothing written before accept

    at.button(key="osm_accept").click().run()
    assert not at.exception, at.exception
    assert len(osm.read_snapshot(ui_env)) == 5
    assert at.success[0].value.startswith("Tilannekuva tallennettu: ")
    assert not at.metric  # the fetched list is gone; the snapshot caption shows the count
    assert any(c.value.endswith("5 pistettä") for c in at.caption)


VF_SAMPLE = Path(__file__).parent / "fixtures" / "visitfinland" / "products_sample.json"


def test_services_page_visit_finland_needs_key_and_municipality(ui_env, monkeypatch):
    from manager.sources import visitfinland

    monkeypatch.setenv("VF_API_KEY", "secret")
    monkeypatch.setattr(visitfinland, "fetch", lambda *a, **kw: pytest.fail("must not fetch"))
    at = AppTest.from_file(str(UI / "views" / "services.py"), default_timeout=10).run()
    assert not at.exception, at.exception
    assert at.button(key="visitfinland_fetch").disabled
    assert "Visit Finland -haku ei ole käytössä: project.json:sta puuttuu municipality." in [
        c.value for c in at.caption
    ]


def test_services_page_visit_finland_fetch_and_accept(ui_env, monkeypatch):
    from manager.sources import visitfinland

    project = json.loads((ui_env / "project.json").read_text(encoding="utf-8"))
    project["municipality"] = "Rovaniemi"
    (ui_env / "project.json").write_text(json.dumps(project), encoding="utf-8")
    monkeypatch.setenv("VF_API_KEY", "secret")
    monkeypatch.setenv("VF_API_URL", "https://vf.test/graphql")
    products = json.loads(VF_SAMPLE.read_text(encoding="utf-8"))["data"]["product"]
    calls = []

    def fake_fetch(city, *, url, key, **kw):
        calls.append((city, url, key))
        return products

    monkeypatch.setattr(visitfinland, "fetch", fake_fetch)
    at = AppTest.from_file(str(UI / "views" / "services.py"), default_timeout=10).run()
    assert not at.button(key="visitfinland_fetch").disabled
    at.button(key="visitfinland_fetch").click().run()
    assert not at.exception, at.exception
    assert calls == [("Rovaniemi", "https://vf.test/graphql", "secret")]
    assert [(m.label, m.value) for m in at.metric] == [
        ("Uusia", "+3"),
        ("Poistuneita", "\u22120"),
        ("Muuttuneita", "0"),
        ("Yhteensä", "3"),
    ]
    table = at.dataframe[0].value
    assert list(table["nimi"]) == ["Ounasvaaran mökit", "Riverside Restaurant", "Pyörävuokraamo"]
    assert list(table["kategoria"]) == ["majoitus", "ravintola", "pyörävuokraus"]
    assert not (ui_env / "services" / "visitfinland.geojson").exists()

    at.button(key="visitfinland_accept").click().run()
    assert not at.exception, at.exception
    assert len(visitfinland.read_snapshot(ui_env)) == 3
    assert not (ui_env / "services" / "osm.geojson").exists()  # the OSM snapshot is untouched
    assert at.success[0].value.startswith("Tilannekuva tallennettu: ")
    assert any(c.value.endswith("3 pistettä") for c in at.caption)


FX_OSM = Path(__file__).parent / "fixtures" / "fx-full" / "services" / "osm.geojson"


def test_services_page_adds_hides_and_deletes_manual_markers(ui_env):
    shutil.copy(FX_OSM, ui_env / "services" / "osm.geojson")
    at = AppTest.from_file(str(UI / "views" / "services.py"), default_timeout=10).run()
    assert not at.exception, at.exception
    # The new point form starts at the centre of the project area (P11: no invented place).
    assert at.number_input(key="new_lon").value == pytest.approx(25.8)
    assert at.number_input(key="new_lat").value == pytest.approx(66.5)
    assert at.selectbox(key="fix_target").options == [
        "osm:node/102 · juomavesi",
        "osm:node/103 · Vaattungin laavu · laavu",
    ]

    at.button(key="FormSubmitter:new_marker-Tallenna piste").click().run()
    assert at.error[0].value == "Anna pisteelle nimi."
    assert store.read_manual(ui_env) == []  # nothing written

    at.text_input(key="new_name_fi").set_value("Kahvila Napa")
    at.selectbox(key="new_category").select("cafe")
    at.number_input(key="new_lon").set_value(25.7294)
    at.number_input(key="new_lat").set_value(66.5031)
    at.text_input(key="new_url").set_value("https://napa.example")
    at.button(key="FormSubmitter:new_marker-Tallenna piste").click().run()
    assert not at.exception, at.exception
    assert at.success[0].value.startswith("Käsin tehdyt merkinnät tallennettu: 1 kpl")
    assert "Aja build, jotta muutos näkyy julkaisudatassa." in [c.value for c in at.caption]
    markers = store.read_manual(ui_env)
    assert [m.id for m in markers] == ["manual:kahvila-napa"]
    assert markers[0].location == (25.7294, 66.5031) and markers[0].url == "https://napa.example"
    assert markers[0].category == "cafe" and markers[0].name == {"fi": "Kahvila Napa"}

    at.selectbox(key="fix_target").select("osm:node/103").run()
    at.button(key="FormSubmitter:fix_marker-Tallenna korjaus").click().run()
    assert at.error[0].value.startswith("Ei muutettavaa")
    at.checkbox(key="hide_osm:node/103").check()
    at.button(key="FormSubmitter:fix_marker-Tallenna korjaus").click().run()
    assert not at.exception, at.exception
    assert at.success[0].value.startswith("Käsin tehdyt merkinnät tallennettu: 2 kpl")
    hidden = next(m for m in store.read_manual(ui_env) if m.replaces == "osm:node/103")
    assert hidden.hidden and hidden.id is None
    assert at.selectbox(key="fix_target").options == ["osm:node/102 · juomavesi"]
    assert len(osm.read_snapshot(ui_env)) == 2  # the snapshot is never touched

    table = at.dataframe[-1].value
    assert list(table.columns) == ["id", "korvaa", "piilotettu", "nimi", "kategoria"]
    assert [list(r) for _, r in table.iterrows()] == [
        ["manual:kahvila-napa", "", False, "Kahvila Napa", "kahvila"],
        ["", "osm:node/103", True, "", ""],
    ]

    # A correction replaces the marker of the same target; a missing target is listed below.
    at.selectbox(key="fix_target").select("osm:node/102").run()
    at.text_input(key="fix_name_osm:node/102_fi").set_value("Lähde")
    at.selectbox(key="fix_category_osm:node/102").select("hut")
    at.button(key="FormSubmitter:fix_marker-Tallenna korjaus").click().run()
    assert not at.exception, at.exception
    fixed = next(m for m in store.read_manual(ui_env) if m.replaces == "osm:node/102")
    assert fixed.overrides() == {"name": {"fi": "Lähde"}, "category": "hut"}
    assert "osm:node/102 · Lähde · tupa" in at.selectbox(key="fix_target").options
    assert at.text_input(key="fix_name_osm:node/102_fi").value == "Lähde"  # prefilled

    at.selectbox(key="delete_marker").select("osm:node/103")
    at.button(key="delete_marker_button").click().run()
    assert not at.exception, at.exception
    assert [store.marker_key(m) for m in store.read_manual(ui_env)] == [
        "manual:kahvila-napa",
        "osm:node/102",
    ]
    assert len(at.selectbox(key="fix_target").options) == 2  # node/103 is back
