"""Check: every written JSON matches its pydantic model (7.2, Schema and Enum values)."""

from pathlib import Path

from pydantic import BaseModel, ValidationError

from manager.models import Catalog, PublishedRoute
from manager.validate.finding import Finding


def error_lines(e: ValidationError) -> list[str]:
    """One readable line per error: the field path and pydantic's message, without the input
    dump and the documentation URL. A wrong enum value reads e.g.
    "segments.0.surface: Input should be 'asphalt', 'paving', 'gravel', ..."."""
    return [
        f"{'.'.join(str(part) for part in err['loc']) or 'root'}: {err['msg']}"
        for err in e.errors()
    ]


def _validate(path: Path, model: type[BaseModel]) -> list[Finding]:
    try:
        model.model_validate_json(path.read_bytes())
    except ValidationError as e:
        return [Finding("error", f"{path.name}: {line}") for line in error_lines(e)]
    except (ValueError, OSError) as e:
        return [Finding("error", f"{path.name}: {e}")]
    return []


def check_schema(tmp_dir: Path) -> list[Finding]:
    findings = _validate(tmp_dir / "catalog.json", Catalog)
    for path in sorted(tmp_dir.glob("routes/*/route.json")):
        findings += _validate(path, PublishedRoute)
    return findings
