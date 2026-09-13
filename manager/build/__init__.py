"""Build: source data → published data through a temporary directory, swapped atomically (7.2)."""

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from manager.build.catalog import build_catalog
from manager.build.errors import BuildError
from manager.build.gpx import export_gpx
from manager.build.media import publish_media
from manager.build.overview import overview
from manager.build.read import read_source_data
from manager.build.routes import process_route, published_route
from manager.build.services import merge, services_collection
from manager.report import presentation_coverage
from manager.validate import CHECKS, Finding, check_all

__all__ = ["BuildError", "BuildReport", "build", "is_stale"]


@dataclass
class BuildReport:
    route_count: int
    first_visit_bytes: int
    warnings: list[str] = field(default_factory=list)
    # Every CHECKS key; warnings and infos only, since an error stops the build.
    findings_by_check: dict[str, list[Finding]] = field(default_factory=dict)
    # Rows of report.presentation_coverage (7.2, report): shown by the build page.
    presentation_coverage: list[dict] = field(default_factory=list)

    @property
    def infos(self) -> list[str]:
        return [
            f.message for fs in self.findings_by_check.values() for f in fs if f.level == "info"
        ]

    def text(self) -> str:
        lines = [
            f"Routes: {self.route_count}",
            f"First-visit size: {self.first_visit_bytes / 1024:.1f} kB",
            f"Warnings: {len(self.warnings)}",
            *(f"  - {w}" for w in self.warnings),
            f"Info: {len(self.infos)}",
            *(f"  - {i}" for i in self.infos),
        ]
        return "\n".join(lines)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def published_form(model: BaseModel) -> dict:
    data = model.model_dump(mode="json", exclude_none=True)
    # Catalog coverage is optional and absent until layers are implemented (5.6).
    if data.get("coverage") == {}:
        del data["coverage"]
    return data


def _swap(tmp: Path, dist_dir: Path) -> None:
    old = dist_dir.with_name(dist_dir.name + ".old")
    if old.exists():
        shutil.rmtree(old)
    if dist_dir.exists():
        dist_dir.rename(old)
    tmp.rename(dist_dir)
    if old.exists():
        shutil.rmtree(old)


def build(data_dir: Path, dist_dir: Path) -> BuildReport:
    """Write to dist.tmp, check, and only after OK replace dist/.

    On failure raises BuildError; dist.tmp is left on disk and the old dist/ is untouched.
    """
    source = read_source_data(data_dir)
    tmp = dist_dir.with_name(dist_dir.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    results = [(route, process_route(directory, route)) for directory, route in source.routes]
    services = merge(source.osm_services, source.visitfinland_services, source.manual_markers)
    published = []
    language = source.project.default_language
    for (directory, _), (route, result) in zip(source.routes, results, strict=True):
        out = tmp / "routes" / route.id
        media = publish_media(directory, route, out)
        # A name without the default language is a validation error below; the id fills in.
        gpx = export_gpx(result.points, route.name.get(language, route.id))
        route_json = published_route(
            route,
            result,
            gpx_bytes=len(gpx),
            media=media,
            services=services.services,
            nearby_m=source.project.nearby_services_m,
            themes=source.themes,
        )
        write_json(out / "route.json", published_form(route_json))
        write_json(out / "track.geojson", result.track)
        (out / route_json.gpx).write_bytes(gpx)
        published.append(route_json)
    write_json(tmp / "overview.geojson", overview(results))
    if services.services:
        write_json(tmp / "services.geojson", services_collection(services.services))
    catalog = build_catalog(source, published, services=bool(services.services))
    write_json(tmp / "catalog.json", published_form(catalog))

    findings = check_all(data_dir, tmp, source, published)
    errors = [x.message for x in findings if x.level == "error"]
    if errors:
        raise BuildError("\n".join(f"- {e}" for e in errors))

    # ponytail: V0 first visit = catalog + overview; V1–V3 add images and basemap tiles.
    first_visit = sum((tmp / n).stat().st_size for n in ("catalog.json", "overview.geojson"))
    _swap(tmp, dist_dir)
    return BuildReport(
        route_count=len(published),
        first_visit_bytes=first_visit,
        warnings=[x.message for x in findings if x.level == "warning"],
        findings_by_check={c: [x for x in findings if x.check == c] for c in CHECKS},
        presentation_coverage=presentation_coverage(source, published),
    )


def is_stale(data_dir: Path, dist_dir: Path) -> bool:
    """True when dist/catalog.json is missing or older than the newest file under data_dir.

    `.git/` is ignored: a commit touches it without changing the content."""
    catalog = dist_dir / "catalog.json"
    if not catalog.is_file():
        return True
    built = catalog.stat().st_mtime
    return any(
        p.is_file() and p.stat().st_mtime > built
        for p in data_dir.rglob("*")
        if ".git" not in p.relative_to(data_dir).parts
    )
