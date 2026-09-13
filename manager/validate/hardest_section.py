"""Check: hardest_section.media is a route media key or a file in the route directory (7.2)."""

from typing import TYPE_CHECKING

from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData


def check_hardest_section(source: "SourceData") -> list[Finding]:
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
    return findings
