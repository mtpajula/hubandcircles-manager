"""Check: ITRS exposure and wilderness are within the project scales (7.2, ITRS values).

Positivity is enforced by the Itrs model; when project.itrs_scales.<dimension> is set, the
value must also be at most that maximum.
"""

from typing import TYPE_CHECKING

from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData

DIMENSIONS = ("exposure", "wilderness")


def check_itrs_values(source: "SourceData") -> list[Finding]:
    findings = []
    for _, route in source.routes:
        if route.itrs is None:
            continue
        for dimension in DIMENSIONS:
            value = getattr(route.itrs, dimension)
            maximum = getattr(source.project.itrs_scales, dimension)
            if value is not None and maximum is not None and value > maximum:
                findings.append(
                    Finding(
                        "error",
                        f"route {route.id}: itrs.{dimension} {value} is outside 1-{maximum}"
                        f" (project.itrs_scales.{dimension})",
                    )
                )
    return findings
