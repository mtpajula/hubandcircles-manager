"""Local preview server for the bundle directory. Stdlib only."""

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

from manager import run
from manager.settings import ROOT

LOG_FILE = ROOT / ".preview.log"  # stdout+stderr of the background preview, for the UI
WORK_DIR = ROOT / ".preview"  # separate from publish's work dir so the two never clobber each other


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
    work_dir: Path = WORK_DIR,
) -> subprocess.Popen:
    """Run `python -m manager preview` as a child process; the caller keeps the handle.

    Output goes to LOG_FILE so a failure (missing frontend, port in use) can be shown."""
    command = [
        sys.executable, "-u", "-m", "manager", "preview",
        "--data", str(data_dir), "--dist", str(dist_dir), "--frontend", str(frontend),
        "--port", str(port), "--work-dir", str(work_dir),
    ]  # fmt: skip
    log = LOG_FILE.open("w", encoding="utf-8")
    log.write(" ".join(command) + "\n")
    log.flush()
    # PYTHONPATH instead of cwd (manager.run explains why); the fault handler leaves a traceback
    # in the log if a native library crashes.
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONFAULTHANDLER": "1"}
    process = run.popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
    log.write(f"pid {process.pid}\n")
    log.close()
    return process


def wait_ready(port: int, process: subprocess.Popen, timeout_s: float = 10) -> bool:
    """True when the server answers on 127.0.0.1:port; False if it exits or the timeout passes."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1):
                return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(0.2)
    return False


def log_tail(lines: int = 15) -> str:
    """Last lines of the preview log, empty if there is none."""
    if not LOG_FILE.is_file():
        return ""
    return "\n".join(LOG_FILE.read_text(encoding="utf-8").splitlines()[-lines:])


def stop(process: subprocess.Popen) -> None:
    """Terminate the preview started with start_background() and wait for it to exit."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
