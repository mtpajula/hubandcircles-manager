"""Models validate the examples of architecture chapter 5 and reject invalid input."""

import pytest
from pydantic import ValidationError

from manager.models import (
    ITRS_LEVEL_NUMBER,
    Catalog,
    Colors,
    GeotiffSource,
    Layer,
    MmlCorridorSource,
    Presentation,
    Project,
    PublishedRoute,
    Route,
    ServicesSource,
    Theme,
    VisibleIn,
    WmsExternalSource,
)

# Chapter 5.1
PROJECT = {
    "name": {"fi": "Napa ja piirit", "en": "Hub & Circles"},
    "subtitle": {"fi": "pyöräillen Rovaniemellä", "en": "cycling the Arctic Circle"},
    "area": [25.40, 66.30, 26.20, 66.70],
    "languages": ["fi", "en"],
    "default_language": "fi",
    "default_theme": "gravel",
    "nearby_services_m": 500,
    "itrs_scales": {"exposure": None, "wilderness": None},
    "feedback": {"github_repo": "user/hubandcircles-data", "issue_form": "trail-issue.yml"},
}

# Chapter 5.2
THEME = {
    "id": "mtb",
    "name": {"fi": "Maasto", "en": "Mountain biking"},
    "tagline": {"fi": "Polut ja tekniset laskut", "en": "Trails and technical descents"},
    "order": 2,
    "colors": {"primary": "#6E4C8F", "route": "#6E4C8F", "highlight": "#E8A33D"},
    "dark": False,
    "basemap": "topo",
    "default_layers": ["services", "lean_tos"],
    "presentation": {
        "key_figures": ["itrs_technical", "itrs_endurance", "length", "ascent"],
        "band": ["elevation", "itrs_technical", "surface"],
        "hero_image": "hardest_section",
        "filters": ["itrs_technical", "length"],
        "service_categories_first": ["water", "lean_to"],
    },
}

# Chapter 5.3, source data
ROUTE = {
    "id": "ounasvaara-north-face",
    "name": {"fi": "Ounasvaaran pohjoisrinne", "en": "Ounasvaara north face"},
    "themes": ["mtb", "gravel"],
    "seasons": ["summer", "autumn"],
    "difficulty": "demanding",
    "track": "track.gpx",
    "cover_image": "media/IMG_2041.jpg",
    "itrs": {
        "technical": "red",
        "endurance": "blue",
        "exposure": 1,
        "wilderness": 2,
        "assessed_by": "M. Pajula",
        "assessed_on": "2026-08-14",
    },
    "winter_maintenance": "groomed",
    "maintenance_url": None,
    "hardest_section": {
        "media": "media/IMG_2102.jpg",
        "km": 19.4,
        "description": {"fi": "Kivikkoinen lasku.", "en": "Rocky descent."},
    },
    "segments": [
        {"start_km": 0.0, "end_km": 4.2, "surface": "asphalt", "traffic": "separated"},
        {"start_km": 4.2, "end_km": 18.7, "surface": "gravel", "traffic": "quiet"},
        {"start_km": 18.7, "end_km": 21.3, "surface": "trail", "itrs_technical": "red"},
    ],
    "maintainer": "non_municipal",
    "lipas_id": None,
    "non_municipal_reasons": ["private_road_no_permission", "unmarked", "unmaintained"],
    "maintenance_note": {"fi": "Yksityistie km 12-17.", "en": "Private road at km 12-17."},
    "sections": [
        {"type": "text", "content": {"fi": "...", "en": "..."}},
        {"type": "gallery", "media": ["media/IMG_2041.jpg", "media/IMG_2057.jpg"]},
        {"type": "video", "url": "https://www.youtube.com/watch?v=..."},
        {"type": "elevation_profile"},
    ],
    "media": {"media/IMG_2041.jpg": {"author": "M. Pajula", "license": "CC BY 4.0"}},
}

# Chapter 5.4: the three layer cards of the architecture (topo and bilberry are V4b sources,
# accepted by the model) and the published guide map.
TOPO_LAYER = {
    "id": "topo",
    "name": {"fi": "Maastokartta", "en": "Topographic map"},
    "slot": "base",
    "source": {
        "method": "mml_corridor",
        "layer": "maastokartta",
        "buffers_m": {"13": 3000, "14": 1500, "15": 800, "16": 400},
        "version": 1,
    },
    "publish_format": "xyz",
    "visible_in": {"themes": "*", "routes": []},
    "default_on": True,
    "minzoom": 10,
    "maxzoom": 16,
    "attribution": "© Maanmittauslaitos, CC BY 4.0",
}
BILBERRY_LAYER = {
    "id": "bilberry-2026",
    "name": {"fi": "Mustikkasatoennuste 2026", "en": "Bilberry yield forecast 2026"},
    "slot": "raster",
    "source": {
        "method": "geotiff",
        "file": "luke/bilberry_2026.tif",
        "classes": [
            {"value": 1, "color": "#f1eef6", "label": {"fi": "Heikko", "en": "Poor"}},
            {"value": 2, "color": "#bdc9e1", "label": {"fi": "Kohtalainen", "en": "Moderate"}},
        ],
    },
    "publish_format": "pmtiles",
    "visible_in": {"themes": ["touring", "gravel"], "routes": ["ounasvaara-gravel"]},
    "default_on": False,
    "opacity": 0.6,
    "attribution": "© Luonnonvarakeskus",
}
GUIDE_MAP_LAYER = {
    "id": "guide-map",
    "name": {"fi": "Opaskartta", "en": "Guide map"},
    "slot": "base",
    "source": {"method": "wms_external"},
    "url": "https://rovaniemi.asiointi.fi/teklaogcweb/WMS.ashx",
    "wms": {"version": "1.1.1", "layers": "Opaskartta", "format": "image/png", "srs": "EPSG:3857"},
    "visible_in": {"themes": ["road", "gravel"], "routes": []},
    "default_on": True,
    "attribution": "© Rovaniemen kaupunki",
}
PUBLISHED_GUIDE_MAP = {k: v for k, v in GUIDE_MAP_LAYER.items() if k != "source"} | {"type": "wms"}

# Chapter 5.6 without the V2 summary fields and without `services`/`coverage`. The
# "..."-abbreviated theme and layer of the architecture are replaced with the chapter 5.2 theme
# and the published 5.4 guide map because both are full models.
CATALOG = {
    "schema_version": 1,
    "generated_at": "2026-09-12T12:00:00Z",
    "project": {
        "name": {"fi": "Napa ja piirit", "en": "Hub & Circles"},
        "subtitle": {"fi": "pyöräillen Rovaniemellä", "en": "cycling the Arctic Circle"},
        "languages": ["fi", "en"],
        "default_language": "fi",
        "default_theme": "gravel",
        "feedback": {"github_repo": "user/hubandcircles-data", "issue_form": "trail-issue.yml"},
    },
    "themes": [THEME],
    "layers": [PUBLISHED_GUIDE_MAP],
    "routes": [
        {
            "id": "ounasvaara-gravel",
            "name": {"fi": "Ounasvaaran gravel-lenkki", "en": "Ounasvaara gravel loop"},
            "themes": ["gravel", "touring"],
            "seasons": ["summer", "autumn"],
            "length_km": 32.4,
            "ascent_m": 410,
            "bbox": [25.72, 66.48, 25.95, 66.56],
            "cover_image": "routes/ounasvaara-gravel/media/cover-3f9a2c-400.webp",
        }
    ],
    "overview": "overview.geojson",
}


def test_project_example():
    p = Project.model_validate(PROJECT)
    assert p.area == (25.40, 66.30, 26.20, 66.70)
    assert p.feedback is not None and p.feedback.issue_form == "trail-issue.yml"
    assert p.itrs_scales.exposure is None and p.itrs_scales.wilderness is None


def test_itrs_scales_must_be_positive():
    Project.model_validate({**PROJECT, "itrs_scales": {"exposure": 4, "wilderness": 3}})
    with pytest.raises(ValidationError):
        Project.model_validate({**PROJECT, "itrs_scales": {"exposure": 0}})


def test_theme_example():
    t = Theme.model_validate(THEME)
    assert t.colors.highlight == "#E8A33D"
    assert t.dark is False and t.tagline == THEME["tagline"]


def test_theme_defaults():
    minimal = {k: v for k, v in THEME.items() if k in {"id", "name", "order", "colors"}}
    t = Theme.model_validate(minimal)
    assert t.tagline is None and t.dark is False and t.default_layers == []


def test_theme_presentation_band_limit():
    Presentation(band=["elevation", "surface", "traffic", "itrs_technical"])
    with pytest.raises(ValidationError, match="lanes besides elevation"):
        Presentation(band=["surface", "traffic", "itrs_technical", "surface"])


@pytest.mark.parametrize(
    "presentation",
    [{"key_figures": ["speed"]}, {"band": ["gradient"]}, {"hero_image": "x"}, {"filters": ["x"]}],
)
def test_theme_presentation_unknown_identifier_rejected(presentation):
    with pytest.raises(ValidationError):
        Theme.model_validate({**THEME, "presentation": presentation})


def test_route_example():
    r = Route.model_validate(ROUTE)
    assert [s.type for s in r.sections] == ["text", "gallery", "video", "elevation_profile"]
    assert r.media["media/IMG_2041.jpg"].author == "M. Pajula"
    assert r.itrs is not None and r.itrs.technical == "red" and r.itrs.wilderness == 2
    assert r.itrs.assessed_on is not None and r.itrs.assessed_on.isoformat() == "2026-08-14"
    assert r.winter_maintenance == "groomed" and r.maintenance_url is None
    assert r.hardest_section is not None and r.hardest_section.km == 19.4
    assert [s.surface for s in r.segments] == ["asphalt", "gravel", "trail"]
    assert r.segments[2].itrs_technical == "red" and r.segments[2].traffic is None
    assert r.non_municipal_reasons[0] == "private_road_no_permission"
    assert r.normalised_fields == []
    # The published form is JSON-serialisable (date as a string) and round-trips.
    PublishedRoute.model_validate(
        {**r.model_dump(mode="json"), "length_km": 21.3, "bbox": [0, 0, 1, 1], "profile": []}
    )


@pytest.mark.parametrize(
    ("legacy", "normalised"),
    [
        ("keskivaikea", "moderate"),
        ("keskivaativa", "moderate"),
        ("helppo", "easy"),
        ("vaativa", "demanding"),
    ],
)
def test_route_legacy_difficulty_normalised(legacy, normalised):
    r = Route.model_validate({**ROUTE, "difficulty": legacy})
    assert r.difficulty == normalised and r.normalised_fields == ["difficulty"]
    # Once normalised, a re-read of the dumped card reports nothing.
    assert Route.model_validate(r.model_dump()).normalised_fields == []


@pytest.mark.parametrize(
    "change",
    [
        {"difficulty": "hard"},
        {"seasons": ["monsoon"]},
        {"winter_maintenance": "sometimes"},
        {"itrs": {"technical": "purple"}},
        {"itrs": {"exposure": 0}},
        {"segments": [{"start_km": 0, "end_km": 1, "surface": "mud"}]},
        {"segments": [{"start_km": 0, "end_km": 1, "traffic": "heavy"}]},
        {"non_municipal_reasons": ["because"]},
        {"hardest_section": {"km": 1.0}},
    ],
    ids=lambda c: next(iter(c)),
)
def test_route_invalid_identifier_rejected(change):
    with pytest.raises(ValidationError):
        Route.model_validate({**ROUTE, **change})


def test_itrs_level_numbers():
    assert ITRS_LEVEL_NUMBER == {"green": 1, "blue": 2, "red": 3, "black": 4, "orange": 5}


def test_route_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Route.model_validate({**ROUTE, "namee": {"fi": "typo"}})


def test_colors_wrong_format_rejected():
    with pytest.raises(ValidationError):
        Colors(primary="red", route="#2F5F96", highlight="#E8A33D")


def test_lang_text_must_not_be_empty():
    with pytest.raises(ValidationError):
        Theme.model_validate({**THEME, "name": {}})


@pytest.mark.parametrize(
    "section",
    [{"type": "text"}, {"type": "unknown"}],
    ids=["text-without-content", "unknown-type"],
)
def test_section_errors(section):
    with pytest.raises(ValidationError):
        Route.model_validate({**ROUTE, "sections": [section]})


def test_catalog_example():
    c = Catalog.model_validate(CATALOG)
    assert c.schema_version == 1
    assert c.layers[0].id == "guide-map" and c.layers[0].type == "wms"
    assert c.layers[0].wms.layers == "Opaskartta" and c.layers[0].legend == []
    assert c.routes[0].bbox == (25.72, 66.48, 25.95, 66.56)
    assert c.services is None and c.coverage == {}


# --- Layer card (5.4) ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("card", "source_type"),
    [
        (TOPO_LAYER, MmlCorridorSource),
        (BILBERRY_LAYER, GeotiffSource),
        (GUIDE_MAP_LAYER, WmsExternalSource),
    ],
    ids=["mml_corridor", "geotiff", "wms_external"],
)
def test_layer_examples_pick_the_source_by_method(card, source_type):
    layer = Layer.model_validate(card)
    assert isinstance(layer.source, source_type)
    assert layer.model_dump(mode="json", exclude_none=True) == {
        "default_on": False,
        "visible_in": {"themes": "*", "routes": []},
        **card,
    }


def test_layer_visible_in_defaults_to_every_theme():
    layer = Layer.model_validate({**GUIDE_MAP_LAYER, "visible_in": {"themes": "*"}})
    assert layer.visible_in.themes == "*" and layer.visible_in.routes == []
    minimal = {k: v for k, v in GUIDE_MAP_LAYER.items() if k != "visible_in"}
    assert Layer.model_validate(minimal).visible_in == VisibleIn()


def test_layer_services_source_and_style():
    layer = Layer.model_validate(
        {
            "id": "shelters",
            "name": {"fi": "Laavut ja tuvat", "en": "Shelters"},
            "slot": "points",
            "source": {"method": "services", "categories": ["lean_to", "hut"]},
            "attribution": "© OpenStreetMap contributors",
            "style": {"color": "#3F6B4A", "icon": "shelter"},
        }
    )
    assert isinstance(layer.source, ServicesSource) and layer.source.categories == [
        "lean_to",
        "hut",
    ]
    assert layer.style.model_dump(exclude_none=True) == {"color": "#3F6B4A", "icon": "shelter"}


@pytest.mark.parametrize(
    "change",
    [
        {"source": {"method": "tile_cache"}},
        {"source": {"method": "wms_external", "layer": "x"}},
        {"source": {"method": "services", "categories": ["sauna"]}},
        {"source": {"method": "xyz_external"}, "url": None},
        {"wms": None},
        {"slot": "overlay"},
        {"opacity": 1.5},
        {"visible_in": {"themes": "all"}},
    ],
    ids=[
        "unknown-method",
        "extra-field",
        "bad-category",
        "xyz-without-url",
        "wms-without-wms",
        "bad-slot",
        "opacity-over-1",
        "themes-not-star",
    ],
)
def test_layer_errors(change):
    with pytest.raises(ValidationError):
        Layer.model_validate({**GUIDE_MAP_LAYER, **change})
