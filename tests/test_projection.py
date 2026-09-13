"""Point → km along the track (7.11), the helper shared by services, images and ride mode."""

import pytest

from manager.build.projection import km_along, km_along_lines
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
