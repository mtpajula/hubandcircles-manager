"""Build stage: overview map. All routes as one lightweight FeatureCollection (7.2)."""

from shapely.geometry import LineString

from manager.build.routes import RouteResult, geometry_lines, line_geometry, simplify
from manager.models import Route

TOLERANCE_M = 20


def overview(routes: list[tuple[Route, RouteResult]]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": route.id, "themes": route.themes},
                "geometry": line_geometry(
                    [
                        simplify(LineString(line), TOLERANCE_M)
                        for line in geometry_lines(result.track["geometry"])
                    ]
                ),
            }
            for route, result in routes
        ],
    }
