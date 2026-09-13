"""Preview as a background process: starts, serves the bundle, stops."""

import socket
import time
import urllib.error
import urllib.request

from manager.publish import preview


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url: str, timeout: float = 8.0) -> int:
    deadline = time.monotonic() + timeout
    while True:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return response.status
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if time.monotonic() > deadline:
                raise
            time.sleep(0.1)


def test_start_and_stop(frontend, dist, tmp_path):
    from .conftest import FIXTURE

    port = _free_port()
    process = preview.start_background(FIXTURE, dist, frontend, port, work_dir=tmp_path)
    try:
        assert _get(f"http://127.0.0.1:{port}/") == 200
        assert _get(f"http://127.0.0.1:{port}/data/catalog.json") == 200
    finally:
        preview.stop(process)
    assert process.poll() is not None
    assert (tmp_path / "bundle" / "index.html").is_file()
