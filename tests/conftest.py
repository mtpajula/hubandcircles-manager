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
