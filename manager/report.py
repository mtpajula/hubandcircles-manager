"""Reports of table 7.2 that never stop a build: presentation coverage per theme."""

from typing import TYPE_CHECKING

from manager.models import PublishedRoute

if TYPE_CHECKING:
    from manager.build.read import SourceData

# Key figures and band lanes that need data entered per route; the rest (length, ascent,
# elevation, longest_service_gap) come from the track or the services.
ROUTE_DATA_ITEMS = (
    "itrs_technical",
    "itrs_endurance",
    "itrs_exposure",
    "itrs_wilderness",
    "surface_shares",
    "surface",
    "traffic",
    "dominant_surface",
    "separated_share",
    "winter_maintenance",
)


def has_item(route: PublishedRoute, item: str, slot: str = "key_figures") -> bool:
    """Whether the published route carries the data behind a key figure or a band lane.

    The band lane `itrs_technical` is drawn from the segments, the key figure from `itrs`.
    """
    if slot == "band" and item == "itrs_technical":
        return route.itrs_technical_shares is not None
    if item.startswith("itrs_"):
        return route.itrs is not None and getattr(route.itrs, item[len("itrs_") :]) is not None
    if item in ("surface_shares", "surface", "dominant_surface"):
        return route.surface_shares is not None
    if item in ("traffic", "separated_share"):
        return route.traffic_shares is not None
    if item == "winter_maintenance":
        return route.winter_maintenance is not None
    return True


def presentation_coverage(source: "SourceData", published: list[PublishedRoute]) -> list[dict]:
    """One row per theme and presentation item that needs route data (7.2, Presentation coverage).

    Row: theme, slot (key_figures | band), item, routes_with_data, routes (of the theme).
    """
    rows = []
    for theme in sorted(source.themes, key=lambda t: t.order):
        if theme.presentation is None:
            continue
        routes = [r for r in published if theme.id in r.themes]
        for slot in ("key_figures", "band"):
            for item in getattr(theme.presentation, slot):
                if item not in ROUTE_DATA_ITEMS:
                    continue
                rows.append(
                    {
                        "theme": theme.id,
                        "slot": slot,
                        "item": item,
                        "routes_with_data": sum(1 for r in routes if has_item(r, item, slot)),
                        "routes": len(routes),
                    }
                )
    return rows
