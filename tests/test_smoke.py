"""Smoke test: fixture → build → bundle → preview. No network, no browser (localhost only)."""

import json
import subprocess
import sys
import threading
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer

from manager.build import build
from manager.models import Catalog, PublishedRoute
from manager.publish import publish
from manager.publish.preview import _Handler

from .conftest import FIXTURE


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_links_resolve(tmp_path):
    dist = tmp_path / "dist"
    build(FIXTURE, dist)
    catalog = Catalog.model_validate(_read(dist / "catalog.json"))
    assert catalog.routes, "fixture data must contain at least one route"

    for summary in catalog.routes:
        directory = dist / "routes" / summary.id
        route = PublishedRoute.model_validate(_read(directory / "route.json"))
        assert route.id == summary.id
        track = _read(directory / route.track)
        assert track["type"] == "Feature"
        assert track["geometry"]["type"] == "LineString"

    overview = _read(dist / catalog.overview)
    assert overview["type"] == "FeatureCollection"
    assert len(overview["features"]) == len(catalog.routes)


def test_bundle_data_path(data, dist, frontend, tmp_path):
    bundle = publish(data, dist, frontend, tmp_path / "work", [], dry_run=True)
    assert (bundle.directory / "index.html").is_file()
    catalog = Catalog.model_validate(_read(bundle.directory / "data" / "catalog.json"))
    # Frontend default VITE_DATA_URL=./data/ (chapter 12.5): catalog paths resolve under it.
    assert (bundle.directory / "data" / catalog.overview).is_file()
    for r in catalog.routes:
        assert (bundle.directory / "data" / "routes" / r.id / "route.json").is_file()


def test_preview_serves_bundle(data, dist, frontend, tmp_path):
    bundle = publish(data, dist, frontend, tmp_path / "work", [], dry_run=True)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(_Handler, directory=str(bundle.directory))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        root = f"http://127.0.0.1:{server.server_address[1]}"
        with urllib.request.urlopen(f"{root}/index.html", timeout=5) as r:
            assert r.status == 200
            assert r.headers["Cache-Control"] == "no-cache"
        with urllib.request.urlopen(f"{root}/data/catalog.json", timeout=5) as r:
            assert r.status == 200
            assert r.headers["Content-Type"].startswith("application/json")
            catalog = Catalog.model_validate(json.loads(r.read()))
        with urllib.request.urlopen(f"{root}/data/{catalog.overview}", timeout=5) as r:
            assert r.status == 200
            assert r.headers["Content-Type"] == "application/geo+json"
            assert r.headers["Cache-Control"] == "no-cache"
            assert json.loads(r.read())["type"] == "FeatureCollection"
        route = catalog.routes[0].id
        with urllib.request.urlopen(f"{root}/data/routes/{route}/route.gpx", timeout=5) as r:
            assert r.status == 200
            assert r.headers["Content-Type"] == "application/gpx+xml"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_each_package_imports_alone():
    # Guards against import cycles that only a fresh interpreter reveals.
    for name in ("manager.build", "manager.validate", "manager.publish"):
        subprocess.run([sys.executable, "-c", f"import {name}"], check=True)
