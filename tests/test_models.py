"""Models validate the examples of architecture chapter 5 and reject invalid input."""

import pytest
from pydantic import ValidationError

from manager.models import Catalog, Colors, Project, Route, Theme

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

# Chapter 5.2 without `presentation` (V2)
THEME = {
    "id": "mtb",
    "name": {"fi": "Maasto", "en": "Mountain biking"},
    "tagline": {"fi": "Polut ja tekniset laskut", "en": "Trails and technical descents"},
    "order": 2,
    "colors": {"primary": "#6E4C8F", "route": "#6E4C8F", "highlight": "#E8A33D"},
    "dark": False,
    "basemap": "topo",
    "default_layers": ["services", "lean_tos"],
}

# Chapter 5.3, source data, without the V2 fields (itrs, winter_maintenance, segments, ...)
ROUTE = {
    "id": "ounasvaara-north-face",
    "name": {"fi": "Ounasvaaran pohjoisrinne", "en": "Ounasvaara north face"},
    "themes": ["mtb", "gravel"],
    "seasons": ["summer", "autumn"],
    "difficulty": "demanding",
    "track": "track.gpx",
    "cover_image": "media/IMG_2041.jpg",
    "sections": [
        {"type": "text", "content": {"fi": "...", "en": "..."}},
        {"type": "gallery", "media": ["media/IMG_2041.jpg", "media/IMG_2057.jpg"]},
        {"type": "video", "url": "https://www.youtube.com/watch?v=..."},
        {"type": "elevation_profile"},
    ],
    "media": {"media/IMG_2041.jpg": {"author": "M. Pajula", "license": "CC BY 4.0"}},
}

# Chapter 5.6 without the V2 summary fields and without `services`/`coverage`. The
# "..."-abbreviated theme of the architecture is replaced with the chapter 5.2 theme because
# Theme is a full model; layers are a free dict until V3, so "..." is fine there.
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
    "layers": [
        {"id": "topo", "type": "xyz", "url": "layers/topo/v3/{z}/{x}/{y}.png", "...": "..."}
    ],
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


def test_route_example():
    r = Route.model_validate(ROUTE)
    assert [s.type for s in r.sections] == ["text", "gallery", "video", "elevation_profile"]
    assert r.media["media/IMG_2041.jpg"].author == "M. Pajula"


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
    assert c.layers[0]["id"] == "topo"
    assert c.routes[0].bbox == (25.72, 66.48, 25.95, 66.56)
    assert c.services is None and c.coverage == {}
