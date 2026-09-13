"""Check: every image the route refers to has a media entry with author and license (7.8)."""

from typing import TYPE_CHECKING

from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData


def check_media(source: "SourceData") -> list[Finding]:
    return [
        Finding(
            "error",
            f"route {route.id}: media info missing for {path!r} (author and license required)",
        )
        for _, route in source.routes
        for path in sorted(route.media_paths())
        if path not in route.media
    ]
