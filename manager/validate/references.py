"""Check: id references point to existing objects (7.2, References)."""

from collections.abc import Iterable
from typing import TYPE_CHECKING

from manager.validate.finding import Finding

if TYPE_CHECKING:
    # Type-only: a runtime import would be circular (build imports validate).
    from manager.build.read import SourceData


def _missing(
    referenced: Iterable[str], existing: set[str], source: str, what: str
) -> list[Finding]:
    return [
        Finding("error", f"{source}: {what} references unknown id {v!r}")
        for v in referenced
        if v not in existing
    ]


def check_references(source: "SourceData", layer_ids: set[str] = frozenset()) -> list[Finding]:
    """layer_ids: ids of published layers. V0: empty, so every layer reference is an error."""
    theme_ids = {t.id for t in source.themes}
    findings = _missing([source.project.default_theme], theme_ids, "project", "default_theme")
    for theme in source.themes:
        where = f"theme {theme.id}"
        basemap = [theme.basemap] if theme.basemap else []
        findings += _missing(basemap, layer_ids, where, "basemap")
        findings += _missing(theme.default_layers, layer_ids, where, "default_layers")
    for _, route in source.routes:
        findings += _missing(route.themes, theme_ids, f"route {route.id}", "themes")
    return findings
