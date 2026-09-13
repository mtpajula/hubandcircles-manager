"""Projection of a point onto the route line (7.11): the km at which the point lies.

The single helper used for service points, image locations and the ride mode. The distance
is measured in metres in EPSG:3067, as every buffer and projection in this package (7.3).
"""

from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import transform

to_m = Transformer.from_crs(4326, 3067, always_xy=True).transform

Coordinates = list[tuple[float, float]]  # WGS84 (lon, lat)


def km_along(track_coords_wgs84: Coordinates, point: tuple[float, float]) -> float:
    """Distance along the track (km, unrounded) to the point of the track nearest to `point`.

    Both arguments are WGS84 (lon, lat). A point beyond either end projects to that end.
    """
    line = transform(to_m, LineString(track_coords_wgs84))
    return line.project(transform(to_m, Point(point))) / 1000
