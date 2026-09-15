"""Point → km along the track (7.11), the helper shared by services, images and ride mode."""

import pytest

from manager.build.projection import TrackProjector, km_along, km_along_lines
from manager.build.routes import process_route
from manager.models import Route

from .conftest import FIXTURE


def test_km_along_fixture_track():
    route = Route(id="t", name={"fi": "t"}, themes=[], seasons=[])
    result = process_route(FIXTURE / "routes" / "test-loop", route)
    coords = result.track["geometry"]["coordinates"]
    # 30 m north of the 4th fixture point (66.5025, 25.726), whose km is 0.407 (see the profile).
    assert km_along(coords, (25.726, 66.5028)) == pytest.approx(0.407, abs=0.01)
    assert km_along(coords, (25.72, 66.5)) == pytest.approx(0.0, abs=0.001)
    # Outside the loop, east of the 6th point (66.501, 25.73) at km 0.672: nearest point wins.
    assert km_along(coords, (25.731, 66.501)) == pytest.approx(0.672, abs=0.01)


def test_km_along_lines_continues_across_parts_without_the_gap():
    part_a = [(25.72, 66.5), (25.72, 66.509)]  # about 1.0 km north
    part_b = [(25.75, 66.5), (25.75, 66.509)]  # 1.3 km east of part_a, same length
    lines = [part_a, part_b]
    assert km_along_lines(lines, (25.72, 66.5045)) == pytest.approx(0.5, abs=0.01)
    # The start of part_b is at km 1.0, not 1.0 + the gap; the nearest part wins.
    assert km_along_lines(lines, (25.751, 66.5)) == pytest.approx(1.0, abs=0.01)
    assert km_along_lines(lines, (25.749, 66.5045)) == pytest.approx(1.5, abs=0.01)
    assert km_along(part_a, (25.72, 66.5045)) == km_along_lines([part_a], (25.72, 66.5045))


def test_snap_moves_a_map_click_onto_the_track_and_point_at_inverts_km():
    """A click beside the line (ADMIN-UI-SPEC 2.6) lands on the line at the same km."""
    part_a = [(25.72, 66.5), (25.72, 66.509)]
    part_b = [(25.75, 66.5), (25.75, 66.509)]
    projector = TrackProjector([part_a, part_b])
    (lon, lat), km = projector.snap((25.7205, 66.5045))  # ~20 m east of part_a
    assert km == pytest.approx(0.5, abs=0.01)
    assert lon == pytest.approx(25.72, abs=1e-6) and lat == pytest.approx(66.5045, abs=1e-4)
    assert km_along_lines([part_a, part_b], (lon, lat)) == pytest.approx(km, abs=1e-6)
    # point_at continues into the second part and clamps beyond the ends.
    lon_b, lat_b = projector.point_at(1.5)
    assert lon_b == pytest.approx(25.75, abs=1e-6) and lat_b == pytest.approx(66.5045, abs=1e-4)
    assert projector.point_at(-1.0) == pytest.approx((25.72, 66.5), abs=1e-6)
    assert projector.point_at(99.0) == pytest.approx((25.75, 66.509), abs=1e-6)
