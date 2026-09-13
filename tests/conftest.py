import shutil
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "data"
EXPECTED = Path(__file__).parent / "fixtures" / "expected"


@pytest.fixture
def data(tmp_path: Path) -> Path:
    """Editable copy of the fixture source data."""
    return shutil.copytree(FIXTURE, tmp_path / "data")


@pytest.fixture(scope="session")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Published data built from the fixture data, shared by the whole session."""
    from manager.build import build

    target = tmp_path_factory.mktemp("build") / "dist"
    build(FIXTURE, target)
    return target


@pytest.fixture
def frontend(tmp_path: Path) -> Path:
    """Smallest possible frontend build: index.html and one hashed asset."""
    fe = tmp_path / "frontend"
    (fe / "assets").mkdir(parents=True)
    (fe / "index.html").write_text("<h1>test</h1>\n")
    (fe / "assets" / "app-abc123.js").write_text("console.log(1)\n")
    return fe


def write_jpeg(
    path: Path,
    location: tuple[float, float] | None = None,
    taken_at: str | None = None,
    size: tuple[int, int] = (800, 600),
) -> Path:
    """Small JPEG with an optional GPS EXIF location (lon, lat) and DateTimeOriginal."""
    from PIL import Image

    exif = Image.Exif()
    if location is not None:
        lon, lat = location
        gps = exif.get_ifd(0x8825)
        gps[1] = "S" if lat < 0 else "N"
        gps[2] = _dms(abs(lat))
        gps[3] = "W" if lon < 0 else "E"
        gps[4] = _dms(abs(lon))
    if taken_at is not None:
        exif.get_ifd(0x8769)[0x9003] = taken_at
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (200, 120, 40)).save(path, "JPEG", exif=exif)
    return path


def _dms(degrees: float) -> tuple[float, float, float]:
    whole = int(degrees)
    minutes = (degrees - whole) * 60
    return (float(whole), float(int(minutes)), round((minutes - int(minutes)) * 60, 4))
