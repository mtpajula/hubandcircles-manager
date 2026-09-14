"""Write source data (route, theme, layer, project) into DATA_DIR. The UI only calls; this
module writes.

Every write goes through write_json (one JSON writer, rule 3 of the skill). The route directory
removal in delete_route, the image removal in remove_media and the card removal in delete_layer
are the only deletions the tool performs.
"""

import re
import shutil
from collections.abc import Iterable
from pathlib import Path

import gpxpy
import gpxpy.gpx

from manager.build import write_json
from manager.build.read import read_features
from manager.models import (
    GallerySection,
    LangText,
    Layer,
    ManualMarker,
    Project,
    Route,
    TextSection,
    Theme,
)
from manager.slug import slugify

__all__ = [
    "StoreError",
    "delete_layer",
    "delete_route",
    "description",
    "manual_id",
    "manual_path",
    "marker_key",
    "media_key",
    "read_manual",
    "remove_media",
    "route_dir",
    "save_layer",
    "save_manual",
    "save_project",
    "save_route",
    "save_theme",
    "slugify",
    "with_description",
]

SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class StoreError(Exception):
    """A write was refused; nothing was written."""


def route_dir(data_dir: Path, route_id: str) -> Path:
    return data_dir / "routes" / route_id


def _check_gpx(gpx: bytes) -> None:
    try:
        parsed = gpxpy.parse(gpx.decode("utf-8"))
    except (UnicodeDecodeError, gpxpy.gpx.GPXException) as e:
        raise StoreError(f"GPX: {e}") from e
    if sum(len(seg.points) for trk in parsed.tracks for seg in trk.segments) < 2:
        raise StoreError("GPX: track has fewer than 2 points")


def media_key(filename: str) -> str:
    """Key of an uploaded image in route.media: media/<slugified stem><lowercase extension>."""
    name = Path(filename)
    return f"media/{slugify(name.stem)}{name.suffix.lower()}"


def save_route(
    data_dir: Path,
    route: Route,
    gpx: bytes | None = None,
    images: list[tuple[str, bytes]] | None = None,
) -> Path:
    """Write routes/<id>/route.json, the track and the images (media_key names) when given.

    Returns the route directory.
    """
    if not SLUG.match(route.id):
        raise StoreError(f"route id {route.id!r} is not a slug (a-z, 0-9, '-')")
    if gpx is not None:
        _check_gpx(gpx)
    directory = route_dir(data_dir, route.id)
    if gpx is None and not (directory / route.track).is_file():
        raise StoreError(f"{directory / route.track}: track is missing; upload a GPX")
    write_json(directory / "route.json", route.model_dump(mode="json", exclude_none=True))
    if gpx is not None:
        (directory / route.track).write_bytes(gpx)
    for filename, data in images or []:
        target = directory / media_key(filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return directory


def remove_media(data_dir: Path, route_id: str, key: str) -> Route:
    """Delete the image file and drop `key` from media, cover, hardest section and galleries.

    The card is rewritten and returned. A missing file is not an error; a key outside media/
    is refused so that the track or the card can never be deleted this way.
    """
    directory = route_dir(data_dir, route_id)
    if not key.startswith("media/") or "/" in key[len("media/") :] or ".." in key:
        raise StoreError(f"{key!r} is not a media key")
    if not (directory / "route.json").is_file():
        raise StoreError(f"{directory}: no such route")
    route = Route.model_validate_json((directory / "route.json").read_bytes())
    sections = [
        s.model_copy(update={"media": [m for m in s.media if m != key]})
        if isinstance(s, GallerySection)
        else s
        for s in route.sections
    ]
    hardest = route.hardest_section
    updated = route.model_copy(
        update={
            "media": {k: v for k, v in route.media.items() if k != key},
            "cover_image": None if route.cover_image == key else route.cover_image,
            "hardest_section": None if hardest and hardest.media == key else hardest,
            "sections": sections,
        }
    )
    (directory / key).unlink(missing_ok=True)
    write_json(directory / "route.json", updated.model_dump(mode="json", exclude_none=True))
    return updated


def delete_route(data_dir: Path, route_id: str) -> None:
    """Remove routes/<id>/ with everything in it. The caller asks for confirmation."""
    directory = route_dir(data_dir, route_id)
    if not SLUG.match(route_id) or not directory.is_dir():
        raise StoreError(f"{directory}: no such route")
    shutil.rmtree(directory)


def save_theme(data_dir: Path, theme: Theme) -> Path:
    path = data_dir / "themes" / f"{theme.id}.json"
    write_json(path, theme.model_dump(mode="json", exclude_none=True))
    return path


def layer_path(data_dir: Path, layer_id: str) -> Path:
    return data_dir / "layers" / f"{layer_id}.json"


def save_layer(data_dir: Path, layer: Layer) -> Path:
    """Write layers/<id>.json (5.4); the id is a slug like a route id."""
    if not SLUG.match(layer.id):
        raise StoreError(f"layer id {layer.id!r} is not a slug (a-z, 0-9, '-')")
    path = layer_path(data_dir, layer.id)
    write_json(path, layer.model_dump(mode="json", exclude_none=True))
    return path


def delete_layer(data_dir: Path, layer_id: str) -> None:
    """Remove layers/<id>.json. Theme references are caught by the build, not here."""
    path = layer_path(data_dir, layer_id)
    if not SLUG.match(layer_id) or not path.is_file():
        raise StoreError(f"{path}: no such layer")
    path.unlink()


def save_project(data_dir: Path, project: Project) -> Path:
    path = data_dir / "project.json"
    write_json(path, project.model_dump(mode="json", exclude_none=True))
    return path


def description(route: Route) -> LangText:
    """Content of the first text section, or {} when there is none."""
    return next((s.content for s in route.sections if isinstance(s, TextSection)), {})


def with_description(route: Route, content: LangText) -> Route:
    """Copy of the route whose first text section holds `content`; other sections untouched.

    Empty content removes the first text section (P11: nothing is written for missing text).
    """
    sections = list(route.sections)
    index = next((i for i, s in enumerate(sections) if isinstance(s, TextSection)), None)
    if index is not None:
        del sections[index]
    if content:
        sections.insert(index or 0, TextSection(type="text", content=content))
    return route.model_copy(update={"sections": sections})


def with_gallery(route: Route, keys: list[str]) -> Route:
    """The route with its gallery section set to `keys` (in media order), removed when empty.

    The gallery is a section so the editor can place it among the texts; the images page keeps it
    in sync with the "in gallery" choice per image.
    """
    others = [s for s in route.sections if s.type != "gallery"]
    if not keys:
        return route.model_copy(update={"sections": others})
    gallery = GallerySection(type="gallery", media=keys)
    position = next((i for i, s in enumerate(route.sections) if s.type == "gallery"), len(others))
    sections = [*others[:position], gallery, *others[position:]]
    return route.model_copy(update={"sections": sections})


# --- Manual markers (5.5) -----------------------------------------------------------------------


def manual_path(data_dir: Path) -> Path:
    return data_dir / "services" / "manual.geojson"


def read_manual(data_dir: Path) -> list[ManualMarker]:
    """The markers of services/manual.geojson; empty without the file."""
    return read_features(manual_path(data_dir), ManualMarker)


def marker_key(marker: ManualMarker) -> str:
    """What identifies a marker: its id for a new point, the target for a correction or hiding."""
    return marker.id or marker.replaces or ""


def save_manual(data_dir: Path, markers: list[ManualMarker]) -> Path:
    """Write services/manual.geojson, ordered by marker key. Snapshots are never touched."""
    path = manual_path(data_dir)
    features = [m.to_feature() for m in sorted(markers, key=marker_key)]
    write_json(path, {"type": "FeatureCollection", "features": features})
    return path


def manual_id(name: str, taken: Iterable[str] = ()) -> str:
    """`manual:<slug>` of the name, with -2, -3 … appended until it is not in `taken`."""
    base = f"manual:{slugify(name) or 'point'}"
    taken = set(taken)
    candidate, n = base, 1
    while candidate in taken:
        n += 1
        candidate = f"{base}-{n}"
    return candidate
