"""Assemble the publish bundle: / = frontend, /data/ = dist, + headers file (chapter 12.5)."""

import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from manager.models import PublishSettings
from manager.publish.errors import PublishError
from manager.publish.headers import cloudflare_headers


@dataclass
class Bundle:
    directory: Path
    file_count: int
    total_bytes: int
    largest: tuple[str, int]  # (path from bundle root, bytes)
    published: list[str] = field(default_factory=list)  # one line per target, set by publish()

    def text(self) -> str:
        name, size = self.largest
        return "\n".join(
            [
                f"Bundle: {self.directory}",
                f"Files: {self.file_count}",
                f"Size: {self.total_bytes / 2**20:.2f} MiB",
                f"Largest file: {name} ({size / 2**20:.2f} MiB)",
            ]
        )


def _unpack_frontend(frontend: Path, target: Path) -> None:
    if frontend.is_dir():
        shutil.copytree(frontend, target, dirs_exist_ok=True)
    elif frontend.is_file() and frontend.suffix == ".zip":
        with zipfile.ZipFile(frontend) as z:
            z.extractall(target)
        # index.html may be at the zip root or in a single subdirectory (e.g. web-v1.4.0/).
        if not (target / "index.html").exists():
            candidates = list(target.glob("*/index.html"))
            if len(candidates) == 1:
                subdir = candidates[0].parent
                for p in subdir.iterdir():
                    shutil.move(p, target / p.name)
                subdir.rmdir()
    else:
        raise PublishError(f"frontend is neither a directory nor a zip: {frontend}")
    if not (target / "index.html").is_file():
        raise PublishError(f"frontend does not contain index.html: {frontend}")
    if (target / "data").exists():
        raise PublishError(f"frontend contains a data/ directory, which is reserved: {frontend}")


def measure(directory: Path) -> Bundle:
    files = [p for p in directory.rglob("*") if p.is_file()]
    sizes = {str(p.relative_to(directory)): p.stat().st_size for p in files}
    largest = max(sizes.items(), key=lambda kv: kv[1], default=("", 0))
    return Bundle(directory, len(sizes), sum(sizes.values()), largest)


def assemble(frontend: Path, dist: Path, settings: PublishSettings, target: Path) -> Bundle:
    """Empty the target and assemble the bundle into it. Failure → PublishError."""
    if not dist.is_dir():
        raise PublishError(f"published data missing, run build first: {dist}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    _unpack_frontend(frontend, target)
    shutil.copytree(dist, target / "data")
    if any(t.type == "cloudflare-pages" for t in settings.targets):
        (target / "_headers").write_text(cloudflare_headers(settings.headers), encoding="utf-8")
    return measure(target)
