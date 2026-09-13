"""Local preview server for the bundle directory. Stdlib only."""

import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

from manager.settings import ROOT


class _Handler(SimpleHTTPRequestHandler):
    # ponytail: no Range requests; PMTiles preview needs them in V4.
    extensions_map: ClassVar[dict[str, str]] = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".geojson": "application/geo+json",
        ".pmtiles": "application/vnd.pmtiles",
    }

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def serve(directory: Path, port: int = 8765) -> None:
    """Serve the directory at http://127.0.0.1:<port>/ until Ctrl-C."""
    handler = partial(_Handler, directory=str(directory))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Preview: http://127.0.0.1:{port}/  (Ctrl-C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print()


def start_background(
    data_dir: Path,
    dist_dir: Path,
    frontend: Path,
    port: int = 8765,
    work_dir: Path = ROOT,
) -> subprocess.Popen:
    """Run `python -m manager preview` as a child process; the caller keeps the handle."""
    command = [
        sys.executable, "-m", "manager", "preview",
        "--data", str(data_dir), "--dist", str(dist_dir), "--frontend", str(frontend),
        "--port", str(port), "--work-dir", str(work_dir),
    ]  # fmt: skip
    return subprocess.Popen(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stop(process: subprocess.Popen) -> None:
    """Terminate the preview started with start_background() and wait for it to exit."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
