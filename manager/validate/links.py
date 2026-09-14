"""Check: every path in published data points to an existing file (7.2, Links)."""

import json
from pathlib import Path

from manager.validate.finding import Finding


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}  # the schema check reports the broken file


def _check(root: Path, path: str | None, source: str) -> list[Finding]:
    if path is None or (root / path).is_file():
        return []
    return [Finding("error", f"{source}: path {path!r} does not point to a file")]


def check_links(tmp_dir: Path) -> list[Finding]:
    catalog = _read(tmp_dir / "catalog.json")
    findings = _check(tmp_dir, catalog.get("overview"), "catalog.json: overview")
    findings += _check(tmp_dir, catalog.get("services"), "catalog.json: services")
    for layer in catalog.get("layers", []):
        if layer.get("type") in ("geojson", "pmtiles"):  # xyz and wms urls are external
            source = f"catalog.json: layer {layer.get('id')}: url"
            findings += _check(tmp_dir, layer.get("url"), source)
    for route in catalog.get("routes", []):
        source = f"catalog.json: route {route.get('id')}: cover_image"
        findings += _check(tmp_dir, route.get("cover_image"), source)
    for route_json in sorted(tmp_dir.glob("routes/*/route.json")):
        route = _read(route_json)
        source = f"{route_json.parent.name}/route.json"
        findings += _check(route_json.parent, route.get("track"), f"{source}: track")
        # cover_image is relative to the data root; media sizes to the route directory (5.3).
        findings += _check(tmp_dir, route.get("cover_image"), f"{source}: cover_image")
        for key, media in route.get("media", {}).items():
            for size, path in media.get("sizes", {}).items():
                findings += _check(route_json.parent, path, f"{source}: media {key!r} size {size}")
    return findings
