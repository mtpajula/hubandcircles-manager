"""Child processes must not fork after pyproj has opened proj.db.

On macOS PROJ registers an atfork handler that closes its SQLite handles in the child, which
segfaults (SIGSEGV inside fork()). Python avoids fork() and uses posix_spawn when the call has
close_fds=False, no cwd and an absolute executable path; every subprocess in the package goes
through manager.run so this holds everywhere.
"""

import subprocess

import pytest
from pyproj import Transformer

from manager import run


@pytest.fixture(autouse=True)
def open_proj_db():
    Transformer.from_crs("EPSG:4326", "EPSG:3067", always_xy=True).transform(25.7, 66.5)


def test_run_after_proj_use(tmp_path):
    result = run.run(["git", "-C", str(tmp_path), "init", "-q"])
    assert result.returncode == 0, result.stderr


def test_popen_after_proj_use(tmp_path):
    log = tmp_path / "log"
    with log.open("w") as f:
        process = run.popen(
            ["python3", "-c", "print('spawned')"], stdout=f, stderr=subprocess.STDOUT
        )
    assert process.wait(timeout=30) == 0
    assert log.read_text().strip() == "spawned"
