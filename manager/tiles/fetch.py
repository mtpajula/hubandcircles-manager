"""MML WMTS tile downloads into the XYZ cache (7.3, 7.5).

The only network code of the tile package. The API key travels as HTTP basic auth (user = key,
empty password), never in a URL or a log line (chapter 13). A single failed tile is reported,
not raised; the build publishes what the cache has.
"""

import base64
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from manager.http import ssl_context
from manager.tiles.mercator import Tile

WMTS_URL = (
    "https://avoin-karttakuva.maanmittauslaitos.fi/avoin/wmts/1.0.0/{layer}/default/"
    "WGS84_Pseudo-Mercator/{z}/{y}/{x}.png"
)
USER_AGENT = "hubandcircles-manager"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# Size guess per tile before the cache has anything to measure (MML maastokartta, PNG).
DEFAULT_TILE_BYTES = 30_000
PROGRESS_EVERY = 100
Progress = Callable[[int, int], None]  # (done, total)


@dataclass
class FetchReport:
    downloaded: int = 0
    cached: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)  # one line per failed tile, without the key

    def text(self) -> str:
        total = self.downloaded + self.cached + self.failed
        return (
            f"{total} tiles needed, {self.cached} cached, {self.downloaded} downloaded, "
            f"{self.failed} failed"
        )


def xyz_path(root: Path, tile: Tile) -> Path:
    """`<root>/{z}/{x}/{y}.png`, the XYZ layout of the cache and of dist/ (7.5)."""
    z, x, y = tile
    return root / str(z) / str(x) / f"{y}.png"


def tile_path(cache_dir: Path, layer_name: str, tile: Tile) -> Path:
    """`<cache>/<layer>/{z}/{x}/{y}.png`: the cache is always XYZ, one tree per WMTS layer."""
    return xyz_path(cache_dir / layer_name, tile)


def cached_tiles(tiles: Iterable[Tile], cache_dir: Path, layer_name: str) -> set[Tile]:
    return {t for t in tiles if tile_path(cache_dir, layer_name, t).is_file()}


def estimate_bytes(tile_count: int, cache_dir: Path, layer_name: str) -> int:
    """Estimated size of `tile_count` tiles: the mean of the cached ones, else a fixed guess."""
    sizes = [p.stat().st_size for p in (cache_dir / layer_name).glob("*/*/*.png")][:2000]
    mean = sum(sizes) / len(sizes) if sizes else DEFAULT_TILE_BYTES
    return int(tile_count * mean)


def _request(url: str, key: str, timeout_s: int) -> bytes:
    token = base64.b64encode(f"{key}:".encode()).decode("ascii")
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Authorization": f"Basic {token}"}
    )
    with urllib.request.urlopen(request, timeout=timeout_s, context=ssl_context()) as response:
        return response.read()


def _fetch_one(tile: Tile, target: Path, layer_name: str, key: str, timeout_s: int) -> str | None:
    """Download one tile, retrying once; returns an error line or None. The file is written
    whole or not at all, so a partial download never counts as cached."""
    z, x, y = tile
    url = WMTS_URL.format(layer=layer_name, z=z, x=x, y=y)
    error = None
    for _ in range(2):
        try:
            content = _request(url, key, timeout_s)
        except (urllib.error.URLError, OSError, ValueError) as e:
            error = f"{z}/{x}/{y}: {e}"
            continue
        if not content.startswith(PNG_MAGIC):
            error = f"{z}/{x}/{y}: not a PNG ({len(content)} bytes)"
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(".part")
        partial.write_bytes(content)
        os.replace(partial, target)
        return None
    return error


def download_missing(
    tiles: Iterable[Tile],
    cache_dir: Path,
    layer_name: str,
    *,
    key: str,
    timeout_s: int = 30,
    max_workers: int = 4,
    progress: Progress | None = None,
) -> FetchReport:
    """Fetch the tiles the cache lacks. `progress(done, total)` is called every 100 tiles."""
    report = FetchReport()
    missing = []
    for tile in sorted(set(tiles)):
        if tile_path(cache_dir, layer_name, tile).is_file():
            report.cached += 1
        else:
            missing.append(tile)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        jobs = [
            pool.submit(
                _fetch_one, t, tile_path(cache_dir, layer_name, t), layer_name, key, timeout_s
            )
            for t in missing
        ]
        for done, job in enumerate(jobs, start=1):
            error = job.result()
            if error is None:
                report.downloaded += 1
            else:
                report.failed += 1
                report.errors.append(error)
            if progress is not None and done % PROGRESS_EVERY == 0:
                progress(done, len(missing))
    return report
