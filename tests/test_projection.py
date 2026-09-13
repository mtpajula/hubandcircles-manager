"""Point → km along the track (7.11), the helper shared by services, images and ride mode."""

import pytest

from manager.build.projection import km_along
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
