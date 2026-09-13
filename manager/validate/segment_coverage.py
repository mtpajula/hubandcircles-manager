"""Check: surface/traffic segments cover enough of a route whose theme band shows them (7.2).

Coverage below MIN_COVERAGE of length_km is a warning: the band would be mostly "unknown".
"""

from typing import TYPE_CHECKING

from manager.models import PublishedRoute
from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData

MIN_COVERAGE = 0.8
LANES = ("surface", "traffic")


def coverage(route: PublishedRoute, attribute: str) -> float:
    """Share of length_km covered by segments that have `attribute`; 0 for a zero-length route."""
    if route.length_km <= 0:
        return 0.0
    covered = sum(
        s.end_km - s.start_km for s in route.segments if getattr(s, attribute) is not None
    )
    return min(1.0, covered / route.length_km)


def check_segment_coverage(source: "SourceData", published: list[PublishedRoute]) -> list[Finding]:
    themes = {t.id: t for t in source.themes}
    findings = []
    for route in published:
        reported: set[str] = set()
        for theme in (themes[t] for t in route.themes if t in themes):
            band = theme.presentation.band if theme.presentation else []
            for lane in (lane for lane in LANES if lane in band and lane not in reported):
                share = coverage(route, lane)
                if share >= MIN_COVERAGE:
                    continue
                reported.add(lane)
                findings.append(
                    Finding(
                        "warning",
                        f"route {route.id}: {lane} segments cover {share:.0%} of the route,"
                        f" below {MIN_COVERAGE:.0%} (band of theme {theme.id})",
                    )
                )
    return findings
