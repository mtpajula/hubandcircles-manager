"""Check: a route in a theme whose key figures show ITRS has that ITRS value (7.2, warning)."""

from typing import TYPE_CHECKING

from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData


def check_itrs_missing(source: "SourceData") -> list[Finding]:
    themes = {t.id: t for t in source.themes}
    findings = []
    for _, route in source.routes:
        reported: set[str] = set()
        for theme in (themes[t] for t in route.themes if t in themes):
            figures = theme.presentation.key_figures if theme.presentation else []
            for figure in figures:
                if not figure.startswith("itrs_"):
                    continue
                dimension = figure.removeprefix("itrs_")
                present = route.itrs is not None and getattr(route.itrs, dimension) is not None
                if present or dimension in reported:
                    continue
                reported.add(dimension)
                findings.append(
                    Finding(
                        "warning",
                        f"route {route.id}: itrs.{dimension} missing, shown as a key figure of"
                        f" theme {theme.id}",
                    )
                )
    return findings
