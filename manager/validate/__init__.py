"""Checks run on the temporary directory and source data before dist/ is swapped (7.2)."""

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from manager.validate.finding import Finding
from manager.validate.links import check_links
from manager.validate.references import check_references
from manager.validate.schema import check_schema
from manager.validate.secrets import check_secrets
from manager.validate.translations import check_translations

if TYPE_CHECKING:
    # Type-only: a runtime import would be circular (build imports validate).
    from manager.build.read import SourceData

__all__ = ["CHECKS", "Finding", "check_all"]

# Check keys in the order of chapter 7.2; the UI lists them in this order.
# ponytail: V2–V4 add manual markers, target limits and theme colour contrast.
CHECKS = ("schema", "links", "references", "translations", "secrets")


def check_all(data_dir: Path, tmp_dir: Path, source: "SourceData") -> list[Finding]:
    """Run every check and tag each finding with the key of the check that produced it."""
    results = {
        "schema": check_schema(tmp_dir),
        "links": check_links(tmp_dir),
        "references": check_references(source),
        "translations": check_translations(source),
        "secrets": check_secrets([data_dir, tmp_dir]),
    }
    assert tuple(results) == CHECKS
    return [replace(f, check=key) for key, findings in results.items() for f in findings]
