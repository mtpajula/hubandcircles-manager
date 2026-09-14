"""Projection of a point onto the route line (7.11): the km at which the point lies.

The single helper used for service points, image locations and the ride mode. The distance
is measured in metres in EPSG:3067, as every buffer and projection in this package (7.3).
"""

from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import transform

# Same as the example in chapter 7.3: metres in EPSG:3067, degrees in WGS84.
to_m = Transformer.from_crs(4326, 3067, always_xy=True).transform
to_deg = Transformer.from_crs(3067, 4326, always_xy=True).transform

Coordinates = list[tuple[float, float]]  # WGS84 (lon, lat)


class TrackProjector:
    """A track of one or more parts (MultiLineString) prepared once for many projections.

    The nearest part wins, and km continues from part to part without the gap between them,
    like `properties.km` of track.geojson (7.11).
    """

    def __init__(self, lines: list[Coordinates]) -> None:
        assert lines, "a track has at least one part"
        self.parts: list[tuple[LineString, float]] = []  # (part in EPSG:3067, start km)
        start_km = 0.0
        for coords in lines:
            line = transform(to_m, LineString(coords))
            self.parts.append((line, start_km))
            start_km += line.length / 1000

    def project(self, point: tuple[float, float]) -> tuple[float, float]:
        """(distance from the track in metres, km along the track) of the nearest track point.

        `point` is WGS84 (lon, lat). A point beyond either end projects to that end.
        """
        target = transform(to_m, Point(point))
        nearest: tuple[float, float] | None = None
        for line, start_km in self.parts:
            distance = line.distance(target)
            if nearest is None or distance < nearest[0]:
                nearest = (distance, start_km + line.project(target) / 1000)
        assert nearest is not None
        return nearest


def km_along(track_coords_wgs84: Coordinates, point: tuple[float, float]) -> float:
    """Distance along the track (km, unrounded) to the point of the track nearest to `point`.

    Both arguments are WGS84 (lon, lat). A point beyond either end projects to that end.
    """
    return km_along_lines([track_coords_wgs84], point)


def km_along_lines(lines: list[Coordinates], point: tuple[float, float]) -> float:
    """km_along for a track of one or more parts; see TrackProjector."""
    return TrackProjector(lines).project(point)[1]
