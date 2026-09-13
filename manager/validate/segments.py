"""Check: segments are ordered, do not overlap and lie within the route (7.2, Segments).

Checked on the source segments: the published ones are already sorted, clamped and gap-filled
(build/segments.py), which would hide exactly these mistakes. The pure rule, segment_problems,
is what the segment editor shows before a save (ADMIN-UI-SPEC 2.6).
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from manager.models import PublishedRoute, Segment
from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData

TOLERANCE_KM = 0.05


def segment_problems(segments: Sequence[Segment], length_km: float) -> list[str]:
    """One message per broken segment: ordering, overlap and the 0…length+tolerance range."""
    limit = length_km + TOLERANCE_KM
    problems = []
    previous_end = 0.0
    for i, s in enumerate(segments):
        where = f"segments[{i}]"
        if s.end_km <= s.start_km:
            problems.append(f"{where}: end_km {s.end_km} is not after start_km {s.start_km}")
        elif s.start_km < previous_end:
            problems.append(
                f"{where}: starts at {s.start_km} km before the previous segment ends"
                f" at {previous_end} km (segments must be ordered and not overlap)"
            )
        if s.start_km < 0 or s.end_km > limit:
            problems.append(
                f"{where}: {s.start_km}-{s.end_km} km is outside 0-{limit:.2f} km"
                f" (length {length_km} km + {TOLERANCE_KM} km)"
            )
        previous_end = max(previous_end, s.end_km)
    return problems


def check_segments(source: "SourceData", published: list[PublishedRoute]) -> list[Finding]:
    length_km = {r.id: r.length_km for r in published}
    return [
        Finding("error", f"route {route.id}: {problem}")
        for _, route in source.routes
        for problem in segment_problems(route.segments, length_km[route.id])
    ]
