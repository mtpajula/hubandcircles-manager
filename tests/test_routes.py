"""The route stage computes the README golden values from the fixture GPX."""

from itertools import pairwise
from pathlib import Path

import gpxpy
import pytest

from manager.build import BuildError
from manager.build.gpx import export_gpx
from manager.build.routes import process_route, published_route
from manager.models import Route, Segment

from .conftest import FIXTURE

ROUTE = Route(id="t", name={"fi": "t"}, themes=[], seasons=[], difficulty="easy")


def _gpx(path: Path, *segments: list[str]) -> Path:
    path.write_text(
        '<gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1"><trk>'
        + "".join("<trkseg>" + "".join(points) + "</trkseg>" for points in segments)
        + "</trk></gpx>"
    )
    return path


def test_fixture_gpx():
    result = process_route(FIXTURE / "routes" / "test-loop", Route(**ROUTE.model_dump()))
    assert result.ascent_m == 29
    assert result.bbox == pytest.approx((25.72, 66.499, 25.73, 66.5025), abs=1e-4)
    assert result.length_km == 1.3
    assert result.profile[0] == (0.0, 100.0)
    assert result.profile[-1] == pytest.approx((1.28, 100.0), abs=0.01)
    assert result.track["geometry"]["type"] == "LineString"
    assert len(result.track["geometry"]["coordinates"]) >= 2


def test_without_elevations(tmp_path):
    _gpx(
        tmp_path / "track.gpx",
        ['<trkpt lat="66.5" lon="25.72"/>', '<trkpt lat="66.501" lon="25.721"/>'],
    )
    result = process_route(tmp_path, ROUTE)
    assert result.ascent_m is None  # unknown, not zero (P11)
    assert result.profile == []
    assert result.length_km == 0.1


def test_single_point_is_error(tmp_path):
    _gpx(tmp_path / "track.gpx", ['<trkpt lat="66.5" lon="25.72"/>'])
    with pytest.raises(BuildError, match="fewer than 2 points"):
        process_route(tmp_path, ROUTE)


def test_profile_thinned_to_200_points(tmp_path):
    points = [
        f'<trkpt lat="{66.5 + i * 1e-4}" lon="25.72"><ele>{i}</ele></trkpt>' for i in range(500)
    ]
    _gpx(tmp_path / "track.gpx", points)
    result = process_route(tmp_path, ROUTE)
    assert len(result.profile) == 200
    assert result.profile[0][1] == 0.0 and result.profile[-1][1] == 499.0
    assert result.ascent_m == 499


ELEVATIONS = [100, 105, 112, 118, 115, 120, 126, 120, 110, 100]


def test_single_missing_elevation_is_skipped(tmp_path):
    """One point without <ele> drops out of the ascent and the profile; the rest still counts."""
    removed = 4  # ele 115: the 118→115 descent and the 115→120 climb are replaced by 118→120
    lines = (FIXTURE / "routes" / "test-loop" / "track.gpx").read_text().splitlines()
    lines[5 + removed] = lines[5 + removed].replace(f"<ele>{ELEVATIONS[removed]}</ele>", "")
    (tmp_path / "track.gpx").write_text("\n".join(lines))

    remaining = ELEVATIONS[:removed] + ELEVATIONS[removed + 1 :]
    expected = sum(max(0, b - a) for a, b in pairwise(remaining))
    assert expected == 29 - 5 + 2  # by hand: 5 (115→120) dropped, 2 (118→120) added

    result = process_route(tmp_path, ROUTE)
    assert result.ascent_m == expected
    assert len(result.profile) == 9
    assert [e for _, e in result.profile] == remaining
    assert result.profile[0] == (0.0, 100.0)
    assert result.profile[-1] == pytest.approx((1.28, 100.0), abs=0.01)


def test_elevation_on_one_point_only(tmp_path):
    _gpx(
        tmp_path / "track.gpx",
        [
            '<trkpt lat="66.5" lon="25.72"><ele>100</ele></trkpt>',
            '<trkpt lat="66.501" lon="25.721"/>',
            '<trkpt lat="66.502" lon="25.722"/>',
        ],
    )
    result = process_route(tmp_path, ROUTE)
    assert result.ascent_m is None
    assert result.profile == []


def test_multi_segment_track(tmp_path):
    """Segments stay separate: MultiLineString, and the gap between them adds no length."""
    first = ['<trkpt lat="66.5" lon="25.72"/>', '<trkpt lat="66.501" lon="25.72"/>']
    second = ['<trkpt lat="66.6" lon="25.72"/>', '<trkpt lat="66.601" lon="25.72"/>']
    _gpx(tmp_path / "track.gpx", first, second)
    result = process_route(tmp_path, ROUTE)
    assert result.track["geometry"]["type"] == "MultiLineString"
    assert len(result.track["geometry"]["coordinates"]) == 2
    assert result.length_km == 0.2  # 2 x 0.11 km; the 11 km gap is not counted
    assert result.bbox == pytest.approx((25.72, 66.5, 25.72, 66.601), abs=1e-4)
    assert result.ascent_m is None


def test_profile_km_continues_across_segments(tmp_path):
    first = [
        '<trkpt lat="66.5" lon="25.72"><ele>100</ele></trkpt>',
        '<trkpt lat="66.501" lon="25.72"><ele>110</ele></trkpt>',
    ]
    second = [
        '<trkpt lat="66.6" lon="25.72"><ele>110</ele></trkpt>',
        '<trkpt lat="66.601" lon="25.72"><ele>115</ele></trkpt>',
    ]
    _gpx(tmp_path / "track.gpx", first, second)
    result = process_route(tmp_path, ROUTE)
    assert result.ascent_m == 15
    assert [km for km, _ in result.profile] == pytest.approx([0.0, 0.112, 0.112, 0.223], abs=2e-3)


def test_single_point_segments_are_dropped(tmp_path):
    _gpx(
        tmp_path / "track.gpx",
        ['<trkpt lat="66.5" lon="25.72"/>'],
        ['<trkpt lat="66.5" lon="25.72"/>', '<trkpt lat="66.501" lon="25.72"/>'],
    )
    result = process_route(tmp_path, ROUTE)
    assert result.track["geometry"]["type"] == "LineString"
    assert result.length_km == 0.1


def test_only_single_point_segments_is_error(tmp_path):
    _gpx(
        tmp_path / "track.gpx",
        ['<trkpt lat="66.5" lon="25.72"/>'],
        ['<trkpt lat="66.6" lon="25.72"/>'],
    )
    with pytest.raises(BuildError, match="fewer than 2 points"):
        process_route(tmp_path, ROUTE)


# --- km array and GPX export (7.11) ---------------------------------------------------------


def test_km_per_coordinate():
    result = process_route(FIXTURE / "routes" / "test-loop", Route(**ROUTE.model_dump()))
    km = result.track["properties"]["km"]
    assert len(km) == len(result.track["geometry"]["coordinates"])
    assert km[0] == 0.0 and km == sorted(km)
    assert km[-1] == pytest.approx(result.length_km, abs=0.05)
    assert all(round(k, 3) == k for k in km)


def test_km_per_part_of_multi_segment_track(tmp_path):
    first = ['<trkpt lat="66.5" lon="25.72"/>', '<trkpt lat="66.501" lon="25.72"/>']
    second = ['<trkpt lat="66.6" lon="25.72"/>', '<trkpt lat="66.601" lon="25.72"/>']
    _gpx(tmp_path / "track.gpx", first, second)
    result = process_route(tmp_path, ROUTE)
    km = result.track["properties"]["km"]
    parts = result.track["geometry"]["coordinates"]
    assert [len(part) for part in km] == [len(part) for part in parts]
    # Continues across parts without the gap, like length_km and the profile.
    assert km[0] == pytest.approx([0.0, 0.112], abs=2e-3)
    assert km[1] == pytest.approx([0.112, 0.223], abs=2e-3)


def test_gpx_export_keeps_only_positions_and_elevations(tmp_path):
    source = (
        '<gpx version="1.1" creator="Private Phone App" xmlns="http://www.topografix.com/GPX/1/1">'
        "<metadata><name>secret</name></metadata>"
        '<wpt lat="66.5" lon="25.72"><name>home</name></wpt>'
        "<trk><name>Original name</name><trkseg>"
        '<trkpt lat="66.5" lon="25.72"><ele>100</ele><time>2026-08-14T10:00:00Z</time></trkpt>'
        '<trkpt lat="66.501" lon="25.721"><time>2026-08-14T10:01:00Z</time></trkpt>'
        "</trkseg><trkseg>"
        '<trkpt lat="66.6" lon="25.72"><ele>110</ele></trkpt>'
        '<trkpt lat="66.601" lon="25.72"><ele>115</ele></trkpt>'
        "</trkseg></trk></gpx>"
    )
    (tmp_path / "track.gpx").write_text(source)
    result = process_route(tmp_path, ROUTE)
    xml = export_gpx(result.points, "Testilenkki")

    text = xml.decode("utf-8")
    assert "<time>" not in text and "<wpt" not in text and "<metadata>" not in text
    assert "secret" not in text and "Original name" not in text and "Private" not in text
    parsed = gpxpy.parse(text)
    assert len(parsed.tracks) == 1 and parsed.tracks[0].name == "Testilenkki"
    assert [len(s.points) for s in parsed.tracks[0].segments] == [2, 2]
    assert [p.elevation for p in parsed.tracks[0].segments[0].points] == [100.0, None]
    assert parsed.tracks[0].segments[1].points[0].latitude == 66.6


def test_published_route_computed_fields():
    route = ROUTE.model_copy(
        update={
            "segments": [
                Segment(start_km=0.0, end_km=0.8, surface="gravel", traffic="separated"),
                Segment(start_km=1.0, end_km=1.3, surface="trail"),
            ]
        }
    )
    result = process_route(FIXTURE / "routes" / "test-loop", route)
    published = published_route(route, result, gpx_bytes=123)
    assert [(s.start_km, s.end_km) for s in published.segments] == [
        (0, 0.8),
        (0.8, 1.0),
        (1.0, 1.3),
    ]
    assert published.surface_shares == {"gravel": 0.62, "trail": 0.23, "unknown": 0.15}
    assert published.traffic_shares == {"separated": 0.62, "unknown": 0.38}
    assert published.itrs_technical_shares is None
    assert published.dominant_surface == "gravel" and published.separated_share == 0.62
    assert published.gpx == "route.gpx" and published.gpx_bytes == 123
    assert published.hardest_section is None
