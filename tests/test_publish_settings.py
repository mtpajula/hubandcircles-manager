"""publish.json validates according to chapter 12.5."""

import json

import pytest
from pydantic import ValidationError

from manager.models import PublishSettings
from manager.models.publish_settings import defaults

EXAMPLE = {
    "frontend": {"repo": "user/hubandcircles-ui", "version": "v1.4.0"},
    "targets": [
        {"id": "primary", "type": "cloudflare-pages", "project": "hubandcircles"},
        {"id": "backup", "type": "github-pages", "repo": "user/hubandcircles-site"},
    ],
    "headers": [
        {"path": "/assets/*", "cache": "immutable"},
        {"path": "/data/**/*.webp", "cache": "immutable"},
        {
            "path": "/data/**/*.pmtiles",
            "cache": "immutable",
            "content_type": "application/vnd.pmtiles",
        },
        {"path": "/data/layers/*/v*/*", "cache": "immutable"},
        {"path": "/data/**/*.gpx", "cache": "short", "content_type": "application/gpx+xml"},
        {"path": "/data/catalog.json", "cache": "short"},
        {"path": "/data/routes/*/route.json", "cache": "short"},
        {"path": "/index.html", "cache": "none"},
    ],
}


def test_example_validates():
    s = PublishSettings.model_validate(EXAMPLE)
    assert [t.type for t in s.targets] == ["cloudflare-pages", "github-pages"]
    assert s.headers[2].content_type == "application/vnd.pmtiles"


def test_unknown_type_rejected():
    broken = json.loads(json.dumps(EXAMPLE))
    broken["targets"][0]["type"] = "netlify"
    with pytest.raises(ValidationError):
        PublishSettings.model_validate(broken)


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        PublishSettings.model_validate({**EXAMPLE, "secret": "x"})


def test_defaults_validate():
    s = defaults()
    assert PublishSettings.model_validate(s.model_dump()) == s
    assert s.targets == [] and s.headers == PublishSettings.model_validate(EXAMPLE).headers
