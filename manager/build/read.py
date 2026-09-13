"""Build stage: read source data (chapter 7.2, 'Read source data' and 'Validate against schema')."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ValidationError

from manager.build.errors import BuildError
from manager.models import ManualMarker, Project, Route, Service, Theme
from manager.validate.schema import error_lines


@dataclass
class SourceData:
    project: Project
    themes: list[Theme]
    routes: list[tuple[Path, Route]]  # (route directory, route card)
    # services/ (5.5): importer snapshots and the manual markers; a missing file is empty.
    osm_services: list[Service] = field(default_factory=list)
    visitfinland_services: list[Service] = field(default_factory=list)
    manual_markers: list[ManualMarker] = field(default_factory=list)


def _read[M: BaseModel](path: Path, model: type[M]) -> M:
    try:
        return model.model_validate_json(path.read_bytes())
    except OSError as e:
        raise BuildError(f"{path}: {e.strerror}") from e
    except ValidationError as e:
        # Field and allowed values per line, e.g. "difficulty: Input should be 'easy', ..."
        raise BuildError("\n".join(f"{path}: {line}" for line in error_lines(e))) from e
    except ValueError as e:
        raise BuildError(f"{path}: {e}") from e


def read_features[M: Service | ManualMarker](path: Path, model: type[M]) -> list[M]:
    """Every feature of a GeoJSON FeatureCollection as `model`; a missing file is empty."""
    if not path.is_file():
        return []
    try:
        collection = json.loads(path.read_text(encoding="utf-8"))
        return [model.from_feature(feature) for feature in collection["features"]]
    except OSError as e:
        raise BuildError(f"{path}: {e.strerror}") from e
    except ValidationError as e:
        raise BuildError("\n".join(f"{path}: {line}" for line in error_lines(e))) from e
    except (ValueError, KeyError, TypeError) as e:
        raise BuildError(f"{path}: {e}") from e


def read_source_data(data_dir: Path) -> SourceData:
    """Read project.json, themes/*.json, routes/*/route.json and services/*. Failure → BuildError."""
    services = data_dir / "services"
    return SourceData(
        project=_read(data_dir / "project.json", Project),
        themes=[_read(p, Theme) for p in sorted((data_dir / "themes").glob("*.json"))],
        routes=[(p.parent, _read(p, Route)) for p in sorted(data_dir.glob("routes/*/route.json"))],
        osm_services=read_features(services / "osm.geojson", Service),
        visitfinland_services=read_features(services / "visitfinland.geojson", Service),
        manual_markers=read_features(services / "manual.geojson", ManualMarker),
    )
