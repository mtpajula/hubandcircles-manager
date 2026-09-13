"""Segment normalisation and shares (5.3, 7.11)."""

import pytest

from manager.build.segments import dominant, normalise, shares
from manager.models import PublishedSegment, Segment


def _seg(start: float, end: float, **attrs) -> Segment:
    return Segment(start_km=start, end_km=end, **attrs)


def _dump(segments: list[PublishedSegment]) -> list[tuple]:
    return [(s.start_km, s.end_km, s.surface, s.traffic, s.itrs_technical) for s in segments]


def test_normalise_sorts_rounds_clamps_and_fills_gaps():
    result = normalise(
        [_seg(4.2049, 18.7, surface="gravel"), _seg(0.5, 4.2, surface="asphalt", traffic="quiet")],
        21.3,
    )
    assert _dump(result) == [
        (0.0, 0.5, None, None, None),  # gap before the first segment
        (0.5, 4.2, "asphalt", "quiet", None),
        (4.2, 18.7, "gravel", None, None),  # 4.2049 rounded to 0.01 km
        (18.7, 21.3, None, None, None),  # gap after the last segment
    ]


def test_normalise_clamps_end_within_tolerance_to_length():
    assert _dump(normalise([_seg(0, 1.35, surface="gravel")], 1.3)) == [
        (0.0, 1.3, "gravel", None, None)
    ]


def test_normalise_without_segments_is_empty():
    assert normalise([], 10.0) == []  # nothing invented (P11)


def test_normalise_survives_overlap():
    """Overlap is a validation error; here the later segment just starts where the previous ends."""
    result = normalise([_seg(0, 0.8, surface="gravel"), _seg(0.7, 1.3, surface="trail")], 1.3)
    assert _dump(result) == [(0.0, 0.8, "gravel", None, None), (0.8, 1.3, "trail", None, None)]


def test_shares_sum_to_one_with_unknown():
    segments = normalise(
        [
            _seg(0, 4.2, surface="asphalt"),
            _seg(4.2, 18.7, surface="gravel"),
            _seg(18.7, 21.3, surface="trail"),
        ],
        21.3,
    )
    result = shares(segments, 21.3, "surface")
    assert result == {"asphalt": 0.2, "gravel": 0.68, "trail": 0.12}
    assert sum(result.values()) == 1.0

    with_gap = normalise([_seg(0, 4.2, surface="asphalt"), _seg(5, 21.3, surface="gravel")], 21.3)
    result = shares(with_gap, 21.3, "surface")
    assert result == {"asphalt": 0.2, "gravel": 0.76, "unknown": 0.04}
    assert sum(result.values()) == 1.0


def test_shares_rounding_drift_goes_to_the_largest():
    # 1/3 each rounds to 0.33 x 3 = 0.99; the first largest gets the 0.01.
    segments = [
        _seg(0, 1, surface="asphalt"),
        _seg(1, 2, surface="gravel"),
        _seg(2, 3, surface="trail"),
    ]
    result = shares(segments, 3.0, "surface")
    assert sum(result.values()) == 1.0
    assert sorted(result.values()) == [0.33, 0.33, 0.34]


def test_shares_none_when_nothing_known():
    assert shares([], 10.0, "surface") is None
    # Segments exist but none carries the attribute: nothing is known about it (P11).
    assert shares([_seg(0, 10, surface="gravel")], 10.0, "traffic") is None


def test_dominant_at_least_half_else_mixed():
    assert dominant({"gravel": 0.5, "asphalt": 0.3, "trail": 0.2}) == "gravel"
    assert dominant({"gravel": 0.49, "asphalt": 0.31, "trail": 0.2}) == "mixed"
    assert dominant({"gravel": 1.0}) == "gravel"
    assert dominant(None) is None


def test_covered_km_counts_segments_that_say_anything():
    from manager.build.segments import covered_km

    assert covered_km([]) == 0.0
    assert covered_km(
        [_seg(0, 1.0, surface="gravel"), _seg(1.0, 1.5), _seg(2.0, 2.4, itrs_technical="red")]
    ) == pytest.approx(1.4)
