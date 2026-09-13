"""Check: a legacy value was found and normalised while reading (7.2, Normalisation, info)."""

from typing import TYPE_CHECKING

from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData


def check_normalisation(source: "SourceData") -> list[Finding]:
    return [
        Finding(
            "info",
            f"route {route.id}: legacy {name} value normalised to {getattr(route, name)!r}",
        )
        for _, route in source.routes
        for name in route.normalised_fields
    ]
