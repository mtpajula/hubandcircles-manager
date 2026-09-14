"""Check: id references point to existing objects (7.2, References)."""

from collections.abc import Iterable
from typing import TYPE_CHECKING

from manager.models import PublishedLayer
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


def check_references(source: "SourceData", layers: list[PublishedLayer] = ()) -> list[Finding]:
    """`layers`: the published layers; a skipped card (validate/layers.py) is not a target."""
    theme_ids = {t.id for t in source.themes}
    route_ids = {r.id for _, r in source.routes}
    slots = {layer.id: layer.slot for layer in layers}
    findings = _missing([source.project.default_theme], theme_ids, "project", "default_theme")
    for theme in source.themes:
        where = f"theme {theme.id}"
        basemap = [theme.basemap] if theme.basemap else []
        findings += _missing(basemap, set(slots), where, "basemap")
        if theme.basemap in slots and slots[theme.basemap] != "base":
            findings.append(
                Finding(
                    "error",
                    f"{where}: basemap {theme.basemap!r} is in slot {slots[theme.basemap]!r},"
                    " not 'base'",
                )
            )
        findings += _missing(theme.default_layers, set(slots), where, "default_layers")
    for _, route in source.routes:
        findings += _missing(route.themes, theme_ids, f"route {route.id}", "themes")
    for layer in source.layers:
        where = f"layer {layer.id}"
        themes = [] if layer.visible_in.themes == "*" else layer.visible_in.themes
        findings += _missing(themes, theme_ids, where, "visible_in.themes")
        findings += _missing(layer.visible_in.routes, route_ids, where, "visible_in.routes")
    return findings
