"""Check: a non-municipal route names at least one reason (7.2, Maintenance reasons).

Reasons on a municipal route are contradictory but harmless: a warning.
"""

from typing import TYPE_CHECKING

from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData


def check_maintenance_reasons(source: "SourceData") -> list[Finding]:
    findings = []
    for _, route in source.routes:
        if route.maintainer == "non_municipal" and not route.non_municipal_reasons:
            findings.append(
                Finding(
                    "error",
                    f"route {route.id}: maintainer is non_municipal but non_municipal_reasons"
                    " is empty",
                )
            )
        elif route.maintainer == "municipal" and route.non_municipal_reasons:
            findings.append(
                Finding(
                    "warning",
                    f"route {route.id}: non_municipal_reasons given although maintainer is"
                    " municipal",
                )
            )
    return findings
