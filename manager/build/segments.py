"""Build stage: segments normalised and their shares of the route length (5.3, 7.11)."""

from collections.abc import Sequence
from typing import Literal

from manager.models import PublishedSegment, Segment

ShareAttribute = Literal["surface", "traffic", "itrs_technical"]

UNKNOWN = "unknown"
MIXED = "mixed"
DOMINANT_MIN_SHARE = 0.5


def normalise(segments: Sequence[Segment], length_km: float) -> list[PublishedSegment]:
    """Sorted, rounded to 0.01 km, clamped to 0…length_km; gaps become all-None segments.

    A gap before the first and after the last segment is filled too, so a non-empty result
    always covers 0…length_km. No segments in → no segments out (P11: nothing invented).
    Overlaps are a validation error (validate/segments.py); here a later segment simply starts
    where the previous one ended, so bad input still yields a list.
    """
    result: list[PublishedSegment] = []
    position = 0.0
    for s in sorted(segments, key=lambda s: s.start_km):
        start = min(max(round(s.start_km, 2), position), length_km)
        end = min(round(s.end_km, 2), length_km)
        if end <= start:
            continue
        if start > position:
            result.append(PublishedSegment(start_km=position, end_km=start))
        result.append(
            PublishedSegment(
                start_km=start,
                end_km=end,
                surface=s.surface,
                traffic=s.traffic,
                itrs_technical=s.itrs_technical,
            )
        )
        position = end
    if result and position < length_km:
        result.append(PublishedSegment(start_km=position, end_km=length_km))
    return result


def shares(
    segments: Sequence[Segment], length_km: float, attribute: ShareAttribute
) -> dict[str, float] | None:
    """Share of length_km per value of `attribute`, 2 decimals, summing to 1.0.

    Uncovered length (gaps and segments without the attribute) is `unknown`; a zero unknown
    share is left out. None when no segment has the attribute: nothing is known (P11).
    """
    covered_km: dict[str, float] = {}
    for s in segments:
        value = getattr(s, attribute)
        if value is not None:
            covered_km[value] = covered_km.get(value, 0.0) + (s.end_km - s.start_km)
    if not covered_km or length_km <= 0:
        return None
    result = {value: round(km / length_km, 2) for value, km in covered_km.items()}
    unknown = round(1.0 - sum(covered_km.values()) / length_km, 2)
    if unknown > 0:
        result[UNKNOWN] = unknown
    # Rounding drift goes to the largest share so that the shares still sum to 1.0.
    largest = max(result, key=result.__getitem__)
    result[largest] = round(result[largest] + 1.0 - sum(result.values()), 2)
    return result


def dominant(surface_shares: dict[str, float] | None) -> str | None:
    """The surface with the largest share when it is at least 50 %, otherwise `mixed`."""
    if not surface_shares:
        return None
    surface, share = max(surface_shares.items(), key=lambda item: item[1])
    return surface if share >= DOMINANT_MIN_SHARE else MIXED
