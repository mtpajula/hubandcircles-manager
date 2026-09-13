"""Checks run on the temporary directory and source data before dist/ is swapped (7.2)."""

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from manager.models import PublishedRoute
from manager.validate.enums import check_enums
from manager.validate.finding import Finding
from manager.validate.hardest_section import check_hardest_section
from manager.validate.itrs_missing import check_itrs_missing
from manager.validate.itrs_values import check_itrs_values
from manager.validate.links import check_links
from manager.validate.maintenance_reasons import check_maintenance_reasons
from manager.validate.manual_markers import check_manual_markers
from manager.validate.media import check_media
from manager.validate.normalisation import check_normalisation
from manager.validate.presentation import check_presentation
from manager.validate.references import check_references
from manager.validate.schema import check_schema
from manager.validate.secrets import check_secrets
from manager.validate.segment_coverage import check_segment_coverage
from manager.validate.segments import check_segments
from manager.validate.theme_contrast import check_theme_contrast
from manager.validate.translations import check_translations

if TYPE_CHECKING:
    # Type-only: a runtime import would be circular (build imports validate).
    from manager.build.read import SourceData

__all__ = ["CHECKS", "Finding", "check_all"]

# Check keys in the order of chapter 7.2; the UI lists them in this order.
# ponytail: target limits (V4) and the two reports are not checks yet.
CHECKS = (
    "schema",
    "enums",
    "links",
    "references",
    "presentation",
    "segments",
    "hardest_section",
    "media",
    "itrs_values",
    "maintenance_reasons",
    "translations",
    "manual_markers",
    "itrs_missing",
    "segment_coverage",
    "normalisation",
    "secrets",
    "theme_contrast",
)


def check_all(
    data_dir: Path, tmp_dir: Path, source: "SourceData", published: list[PublishedRoute]
) -> list[Finding]:
    """Run every check and tag each finding with the key of the check that produced it."""
    results = {
        "schema": check_schema(tmp_dir),
        "enums": check_enums(source),
        "links": check_links(tmp_dir),
        "references": check_references(source),
        "presentation": check_presentation(source),
        "segments": check_segments(source, published),
        "hardest_section": check_hardest_section(source, published),
        "media": check_media(source),
        "itrs_values": check_itrs_values(source),
        "maintenance_reasons": check_maintenance_reasons(source),
        "translations": check_translations(source),
        "manual_markers": check_manual_markers(source),
        "itrs_missing": check_itrs_missing(source),
        "segment_coverage": check_segment_coverage(source, published),
        "normalisation": check_normalisation(source),
        "secrets": check_secrets([data_dir, tmp_dir]),
        "theme_contrast": check_theme_contrast(source),
    }
    assert tuple(results) == CHECKS
    return [replace(f, check=key) for key, findings in results.items() for f in findings]
