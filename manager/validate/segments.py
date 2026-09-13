"""Check: segments are ordered, do not overlap and lie within the route (7.2, Segments).

Checked on the source segments: the published ones are already sorted, clamped and gap-filled
(build/segments.py), which would hide exactly these mistakes.
"""

from typing import TYPE_CHECKING

from manager.models import PublishedRoute
from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData

TOLERANCE_KM = 0.05


def check_segments(source: "SourceData", published: list[PublishedRoute]) -> list[Finding]:
    length_km = {r.id: r.length_km for r in published}
    findings = []
    for _, route in source.routes:
        limit = length_km[route.id] + TOLERANCE_KM
        previous_end = 0.0
        for i, s in enumerate(route.segments):
            where = f"route {route.id}: segments[{i}]"
            if s.end_km <= s.start_km:
                findings.append(
                    Finding(
                        "error", f"{where}: end_km {s.end_km} is not after start_km {s.start_km}"
                    )
                )
            elif s.start_km < previous_end:
                findings.append(
                    Finding(
                        "error",
                        f"{where}: starts at {s.start_km} km before the previous segment ends"
                        f" at {previous_end} km (segments must be ordered and not overlap)",
                    )
                )
            if s.start_km < 0 or s.end_km > limit:
                findings.append(
                    Finding(
                        "error",
                        f"{where}: {s.start_km}-{s.end_km} km is outside 0-{limit:.2f} km"
                        f" (length {length_km[route.id]} km + {TOLERANCE_KM} km)",
                    )
                )
            previous_end = max(previous_end, s.end_km)
    return findings
