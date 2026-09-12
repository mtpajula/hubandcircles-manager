"""Local preview server for the bundle directory. Stdlib only."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar


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
