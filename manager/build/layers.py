"""Build stage: layers (5.4, 7.2 'Service layer GeoJSONs' and 'Tile layers from the cache').

The published card is the frontend side of the layer card: `type` comes from the source method,
`url` is the external address or the written file, `fetched_at` the newest snapshot the layer
was made from. Source methods outside BUILT_METHODS are skipped; validate/layers.py warns.
"""

import hashlib
import json
from pathlib import Path

from manager.build.errors import BuildError
from manager.build.services import services_collection
from manager.models import BUILT_METHODS, Layer, PublishedLayer, Service

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


def publish_layer(
    layer: Layer, services: list[Service], data_dir: Path, tmp: Path
) -> PublishedLayer | None:
    """The published card, writing layers/<id>-<hash6>.geojson for file-backed layers.
    None when the source method is not built yet."""
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
        assert source.method not in BUILT_METHODS
        return None
    name = layer_file_name(layer.id, content, ".geojson")
    (tmp / "layers").mkdir(parents=True, exist_ok=True)
    (tmp / "layers" / name).write_bytes(content)
    fields["url"] = f"layers/{name}"
    return PublishedLayer(**fields, type=TYPE_BY_METHOD[source.method], fetched_at=fetched_at)


def publish_layers(
    layers: list[Layer], services: list[Service], data_dir: Path, tmp: Path
) -> list[PublishedLayer]:
    """Every buildable layer in card order (chapter 8: order within a slot follows the list)."""
    published = [publish_layer(layer, services, data_dir, tmp) for layer in layers]
    return [layer for layer in published if layer is not None]
