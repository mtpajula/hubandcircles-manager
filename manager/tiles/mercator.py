"""Web Mercator (EPSG:3857) XYZ tile arithmetic, pure functions. No mercantile dependency."""

import math
from collections.abc import Iterator

Tile = tuple[int, int, int]  # (z, x, y)
MAX_LATITUDE = 85.05112878  # the Mercator square ends here; clamp to keep y in range


def tile_for(lon: float, lat: float, z: int) -> tuple[int, int]:
    """(x, y) of the tile containing the WGS84 point at zoom z."""
    n = 1 << z
    lat_rad = math.radians(max(-MAX_LATITUDE, min(MAX_LATITUDE, lat)))
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def tile_bounds(x: int, y: int, z: int) -> tuple[float, float, float, float]:
    """WGS84 (west, south, east, north) of the tile."""
    n = 1 << z

    def lat(row: int) -> float:
        return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * row / n))))

    return (x / n * 360.0 - 180.0, lat(y + 1), (x + 1) / n * 360.0 - 180.0, lat(y))


def tiles_covering(bounds: tuple[float, float, float, float], z: int) -> Iterator[Tile]:
    """Every tile at zoom z that touches the WGS84 (west, south, east, north) box."""
    west, south, east, north = bounds
    x0, y0 = tile_for(west, north, z)
    x1, y1 = tile_for(east, south, z)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            yield (z, x, y)
