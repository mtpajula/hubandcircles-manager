"""Build stage: media. Source images → WebP sizes without metadata, EXIF location (5.3, 7.11, 13).

Published files carry no EXIF, ICC or XMP: the device metadata of the original must not leak
(chapter 13). Only the location and the date are read from the EXIF, into route.json.
"""

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from manager.build.errors import BuildError
from manager.models import PublishedMedia, Route
from manager.slug import slugify

WIDTHS = (400, 1600)
QUALITY = 80

# EXIF tags (CIPA DC-008): the GPS IFD pointer and its entries, the Exif IFD pointer and dates.
GPS_IFD = 0x8825
GPS_LATITUDE_REF, GPS_LATITUDE, GPS_LONGITUDE_REF, GPS_LONGITUDE = 1, 2, 3, 4
EXIF_IFD = 0x8769
DATETIME_ORIGINAL = 0x9003
DATETIME = 0x0132


@dataclass
class ExifInfo:
    location: tuple[float, float] | None = None  # WGS84 (lon, lat)
    taken_at: datetime | None = None


def _degrees(value, ref) -> float | None:
    """Degrees, minutes, seconds as rationals → decimal degrees; None for anything broken."""
    try:
        d, m, s = (float(x) for x in value)
    except (TypeError, ValueError):
        return None
    degrees = d + m / 60 + s / 3600
    if not math.isfinite(degrees):
        return None
    return -degrees if ref in ("S", "W") else degrees


def _parse_datetime(value) -> datetime | None:
    try:
        # EXIF dates are camera local time without a zone; only the date is published.
        return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")  # noqa: DTZ007
    except ValueError:
        return None


def read_exif(path: Path) -> ExifInfo:
    """Location and date from the image EXIF. Anything missing or partial → None (P11)."""
    try:
        with Image.open(path) as image:
            exif = image.getexif()
    except (OSError, UnidentifiedImageError):
        return ExifInfo()
    gps = exif.get_ifd(GPS_IFD)
    lat = _degrees(gps.get(GPS_LATITUDE), gps.get(GPS_LATITUDE_REF))
    lon = _degrees(gps.get(GPS_LONGITUDE), gps.get(GPS_LONGITUDE_REF))
    location = (round(lon, 6), round(lat, 6)) if lat is not None and lon is not None else None
    taken = exif.get_ifd(EXIF_IFD).get(DATETIME_ORIGINAL) or exif.get(DATETIME)
    return ExifInfo(location=location, taken_at=_parse_datetime(taken) if taken else None)


def publish_image(source: Path, out_dir: Path, stem: str) -> dict[str, str]:
    """Write <stem>-<hash>-400.webp and -1600.webp under out_dir (chapter 6), all metadata stripped.

    Returns {"400": "media/<file>", "1600": "media/<file>"} relative to the route directory.
    The hash is the first 6 hex digits of the source's sha256; an existing target is skipped.
    Smaller sources are never upscaled. Orientation is applied before the EXIF is dropped.
    """
    try:
        digest = hashlib.sha256(source.read_bytes()).hexdigest()[:6]
    except OSError as e:
        raise BuildError(f"{source}: {e.strerror}") from e
    targets = {w: out_dir / f"{stem}-{digest}-{w}.webp" for w in WIDTHS}
    if not all(t.is_file() for t in targets.values()):
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(source) as opened:
                image = ImageOps.exif_transpose(opened)
        except (OSError, UnidentifiedImageError) as e:
            raise BuildError(f"{source}: not a readable image ({e})") from e
        for width, target in targets.items():
            if target.is_file():
                continue
            resized = image
            if image.width > width:
                resized = image.resize((width, round(image.height * width / image.width)))
            # No exif=, icc_profile= or xmp=: the published file carries no metadata (13).
            resized.save(target, "WEBP", quality=QUALITY)
    return {str(w): f"{out_dir.name}/{t.name}" for w, t in targets.items()}


def publish_media(directory: Path, route: Route, route_out: Path) -> dict[str, PublishedMedia]:
    """Every image of the route that has author and license: sizes, location and date (5.3).

    A referenced path without a media entry is left out here; the `media` check reports it.
    """
    published = {}
    for path in sorted(route.media_paths()):
        info = route.media.get(path)
        if info is None:
            continue
        source = directory / path
        stem = "cover" if path == route.cover_image else slugify(source.stem)
        sizes = publish_image(source, route_out / "media", stem)
        exif = read_exif(source)
        published[path] = PublishedMedia(
            author=info.author,
            license=info.license,
            sizes=sizes,
            location=exif.location,
            taken_at=exif.taken_at.date().isoformat() if exif.taken_at else None,
        )
    return published
