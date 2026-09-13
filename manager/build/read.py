"""Build stage: read source data (chapter 7.2, 'Read source data' and 'Validate against schema')."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from manager.build.errors import BuildError
from manager.models import Project, Route, Theme
from manager.validate.schema import error_lines


@dataclass
class SourceData:
    project: Project
    themes: list[Theme]
    routes: list[tuple[Path, Route]]  # (route directory, route card)


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


def read_source_data(data_dir: Path) -> SourceData:
    """Read project.json, themes/*.json and routes/*/route.json. Failure → BuildError."""
    return SourceData(
        project=_read(data_dir / "project.json", Project),
        themes=[_read(p, Theme) for p in sorted((data_dir / "themes").glob("*.json"))],
        routes=[(p.parent, _read(p, Route)) for p in sorted(data_dir.glob("routes/*/route.json"))],
    )
