"""Check: every written JSON matches its pydantic model (7.2, Schema)."""

from pathlib import Path

from pydantic import BaseModel, ValidationError

from manager.models import Catalog, PublishedRoute
from manager.validate.finding import Finding


def _validate(path: Path, model: type[BaseModel]) -> list[Finding]:
    try:
        model.model_validate_json(path.read_bytes())
    except (ValidationError, ValueError, OSError) as e:
        return [Finding("error", f"{path.name}: schema mismatch: {e}")]
    return []


def check_schema(tmp_dir: Path) -> list[Finding]:
    findings = _validate(tmp_dir / "catalog.json", Catalog)
    for path in sorted(tmp_dir.glob("routes/*/route.json")):
        findings += _validate(path, PublishedRoute)
    return findings
