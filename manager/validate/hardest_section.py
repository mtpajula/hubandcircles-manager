"""Check: hardest_section.media is a route media key or a file in the route directory (7.2)."""

from typing import TYPE_CHECKING

from manager.models import PublishedRoute
from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData


def check_hardest_section(source: "SourceData", published: list[PublishedRoute]) -> list[Finding]:
    findings = []
    for directory, route in source.routes:
        section = route.hardest_section
        if section is None or section.media in route.media or (directory / section.media).is_file():
            continue
        findings.append(
            Finding(
                "error",
                f"route {route.id}: hardest_section.media {section.media!r} is neither a key of"
                " media nor a file in the route directory",
            )
        )
    # km stays None when the source has none and the image has no EXIF location (P11).
    for route in published:
        if route.hardest_section is not None and route.hardest_section.km is None:
            findings.append(
                Finding(
                    "warning",
                    f"route {route.id}: hardest_section.km missing and image has no location",
                )
            )
    return findings
