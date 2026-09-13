"""Write source data (route, theme, project) into DATA_DIR. The UI only calls; this module writes.

Every write goes through write_json (one JSON writer, rule 3 of the skill). The route directory
removal in delete_route is the only deletion the tool performs.
"""

import re
import shutil
from pathlib import Path

import gpxpy
import gpxpy.gpx

from manager.build import write_json
from manager.models import LangText, Project, Route, TextSection, Theme
from manager.slug import slugify

__all__ = [
    "StoreError",
    "delete_route",
    "description",
    "media_key",
    "route_dir",
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
