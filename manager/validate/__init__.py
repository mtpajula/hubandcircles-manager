"""Checks run on the temporary directory and source data before dist/ is swapped (7.2)."""

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

__all__ = ["Finding", "check_all"]


def check_all(data_dir: Path, tmp_dir: Path, source: "SourceData") -> list[Finding]:
    # ponytail: V2–V4 add manual markers, target limits and theme colour contrast.
    return (
        check_schema(tmp_dir)
        + check_links(tmp_dir)
        + check_references(source)
        + check_translations(source)
        + check_secrets([data_dir, tmp_dir])
    )
