"""Build stage: layers (5.4, 7.2 'Service layer GeoJSONs' and 'Tile layers from the cache').

The published card is the frontend side of the layer card: `type` comes from the source method,
`url` is the external address or the written file, `fetched_at` the newest snapshot the layer
was made from. Source methods outside BUILT_METHODS are skipped; validate/layers.py warns.

`mml_corridor` layers (7.3) are copied from the tile cache, never downloaded here (P5): the
tile set comes from the tracks of the routes the layer is offered with, the coverage is the
widest corridor, and tiles missing from the cache are a warning, not an error.
"""

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from manager.build.errors import BuildError
from manager.build.routes import geometry_lines, process_route
from manager.build.services import services_collection
from manager.models import BUILT_METHODS, Bbox, Layer, PublishedLayer, Route, Service
from manager.tiles.corridor import Coordinates, corridor_tiles, coverage_geojson
from manager.tiles.fetch import xyz_path
from manager.tiles.mercator import Tile

if TYPE_CHECKING:
    from manager.build.read import SourceData

# The tracks the corridor layers are computed from: (route card, track parts in WGS84).
Tracks = list[tuple[Route, list[Coordinates]]]
FETCH_TILES_HINT = "run `python -m manager fetch tiles`"

# Card fields copied as they are; `url` stays for external layers and is replaced for files.
LAYER_FIELDS = set(PublishedLayer.model_fields) - {"type", "fetched_at", "legend"}
# Published type per source method (5.4); the tile sources take theirs from `publish_format`.
TYPE_BY_METHOD = {
    "wms_external": "wms",
    "xyz_external": "xyz",
    "services": "geojson",
    "geojson_file": "geojson",
}


def layer_type(layer: Layer) -> str | None:
    """The published `type` of the card, None when it is not decided yet."""
    return TYPE_BY_METHOD.get(layer.source.method, layer.publish_format)


def layer_file_name(layer_id: str, content: bytes, suffix: str) -> str:
    """`<id>-<hash6>.<suffix>`: the content hash in the name makes the file immutable (P6)."""
    return f"{layer_id}-{hashlib.sha256(content).hexdigest()[:6]}{suffix}"


def _geojson_bytes(collection: dict) -> bytes:
    return (json.dumps(collection, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _read_geojson(path: Path) -> dict:
    try:
        collection = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise BuildError(f"{path}: {e.strerror}") from e
    except ValueError as e:
        raise BuildError(f"{path}: {e}") from e
    if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection":
        raise BuildError(f"{path}: not a GeoJSON FeatureCollection")
    return collection


@dataclass
class LayerOutput:
    """What the layer stage hands to the catalog: the cards, the coverage files, warnings."""

    layers: list[PublishedLayer] = field(default_factory=list)
    coverage: dict[str, str] = field(default_factory=dict)  # layer id -> path under dist/
    warnings: list[str] = field(default_factory=list)


def corridor_lines(layer: Layer, tracks: Tracks) -> list[Coordinates]:
    """Track parts of the routes the layer is available with (5.4 `available`)."""
    themes = layer.visible_in.themes
    return [
        part
        for route, parts in tracks
        if themes == "*" or set(route.themes) & set(themes) or route.id in layer.visible_in.routes
        for part in parts
    ]


def corridor_buffers(layer: Layer) -> dict[int, int]:
    return {int(z): m for z, m in layer.source.buffers_m.items()}


def corridor_tile_set(layer: Layer, tracks: Tracks, area: Bbox | None) -> set[Tile]:
    """Tiles of an `mml_corridor` layer: the per-zoom corridors clipped to the project area."""
    return corridor_tiles(corridor_lines(layer, tracks), corridor_buffers(layer), area)


def read_tracks(data: "SourceData") -> Tracks:
    """Tracks of every route from the source data, for the fetch command and the layers page."""
    return [
        (route, geometry_lines(process_route(directory, route).track["geometry"]))
        for directory, route in data.routes
    ]


def corridor_layers(data: "SourceData", layer_id: str | None = None) -> list[Layer]:
    return [
        layer
        for layer in data.layers
        if layer.source.method == "mml_corridor" and layer_id in (None, layer.id)
    ]


def copy_tiles(tiles: set[Tile], cache: Path, target: Path) -> tuple[list[Tile], int]:
    """Copy the cached tiles into the XYZ tree under `target`; a target file of the same size
    is left alone. Returns (missing tiles, newest cache mtime as a UNIX timestamp)."""
    missing = []
    newest = 0
    for tile in sorted(tiles):
        source = xyz_path(cache, tile)
        if not source.is_file():
            missing.append(tile)
            continue
        stat = source.stat()
        newest = max(newest, int(stat.st_mtime))
        out = xyz_path(target, tile)
        if out.is_file() and out.stat().st_size == stat.st_size:
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, out)
    return missing, newest


def publish_corridor(
    layer: Layer, tracks: Tracks, area: Bbox | None, cache_dir: Path, tmp: Path, out: LayerOutput
) -> PublishedLayer:
    """XYZ tiles under layers/<id>/v<N>/ from the cache plus layers/<id>-coverage.geojson."""
    source = layer.source
    lines = corridor_lines(layer, tracks)
    buffers = corridor_buffers(layer)
    tiles = corridor_tiles(lines, buffers, area)
    target = tmp / "layers" / layer.id / f"v{source.version}"
    missing, newest = copy_tiles(tiles, cache_dir / source.layer, target)
    if missing:
        out.warnings.append(
            f"layer {layer.id}: {len(missing)} of {len(tiles)} tiles missing from the cache"
            f" – {FETCH_TILES_HINT}"
        )
    coverage_name = f"layers/{layer.id}-coverage.geojson"
    (tmp / "layers").mkdir(parents=True, exist_ok=True)
    (tmp / coverage_name).write_bytes(
        _geojson_bytes(coverage_geojson(lines, max(buffers.values()), area))
    )
    out.coverage[layer.id] = coverage_name
    fields = layer.model_dump(include=LAYER_FIELDS)
    fields.update(
        url=f"layers/{layer.id}/v{source.version}/{{z}}/{{x}}/{{y}}.png",
        minzoom=min(buffers),
        maxzoom=max(buffers),
    )
    fetched_at = (
        datetime.fromtimestamp(newest, UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if newest else None
    )
    return PublishedLayer(**fields, type="xyz", fetched_at=fetched_at)


def publish_layer(
    layer: Layer, services: list[Service], data_dir: Path, tmp: Path
) -> PublishedLayer | None:
    """The published card, writing layers/<id>-<hash6>.geojson for file-backed layers.
    None when the source method is not built here (corridors: publish_corridor)."""
    source = layer.source
    fields = layer.model_dump(include=LAYER_FIELDS)
    fetched_at = None
    if source.method in ("wms_external", "xyz_external"):
        return PublishedLayer(**fields, type=TYPE_BY_METHOD[source.method])
    if source.method == "services":
        chosen = [s for s in services if s.category in source.categories]
        content = _geojson_bytes(services_collection(chosen))
        fetched_at = max((s.fetched_at for s in chosen if s.fetched_at), default=None)
    elif source.method == "geojson_file":
        content = _geojson_bytes(_read_geojson(data_dir / source.file))
    else:
        assert source.method not in BUILT_METHODS - {"mml_corridor"}
        return None
    name = layer_file_name(layer.id, content, ".geojson")
    (tmp / "layers").mkdir(parents=True, exist_ok=True)
    (tmp / "layers" / name).write_bytes(content)
    fields["url"] = f"layers/{name}"
    return PublishedLayer(**fields, type=TYPE_BY_METHOD[source.method], fetched_at=fetched_at)


def publish_layers(
    layers: list[Layer],
    services: list[Service],
    data_dir: Path,
    tmp: Path,
    *,
    tracks: Tracks = (),
    area: Bbox | None = None,
    cache_dir: Path | None = None,
) -> LayerOutput:
    """Every buildable layer in card order (chapter 8: order within a slot follows the list)."""
    out = LayerOutput()
    for layer in layers:
        if layer.source.method == "mml_corridor":
            assert cache_dir is not None, "corridor layers need the tile cache"
            published = publish_corridor(layer, list(tracks), area, cache_dir, tmp, out)
        else:
            published = publish_layer(layer, services, data_dir, tmp)
        if published is not None:
            out.layers.append(published)
    return out
