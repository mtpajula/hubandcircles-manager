"""Visit Finland DataHub: tourism services that complement OSM (chapter 7.6).

The DataHub is a Hasura GraphQL API behind Business Finland's API gateway; the subscription key
travels in the `ocp-apim-subscription-key` header. fetch() is the only function that touches
the network; the rest is pure and tested offline. The snapshot services/visitfinland.geojson is
written only after the result is parsed and accepted, exactly like the OSM one.
"""

import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from manager.build import write_json
from manager.build.read import read_features
from manager.build.services import services_collection
from manager.http import ssl_context
from manager.models import Service
from manager.settings import env
from manager.sources.snapshot import Diff, diff  # noqa: F401  (re-exported for callers)

VF_API_URL = "https://api.businessfinland.fi/traveldatahub"
PAGE_SIZE = 500
DESCRIPTION_MAX = 500

# Product type -> category (7.6). rental_service is a bike rental only with one of the tags
# below; every other type (experience, event, attraction, ...) has no category and is skipped.
TYPE_CATEGORIES = {"accommodation": "accommodation", "restaurant": "restaurant", "shop": "shop"}
BIKE_RENTAL_TAGS = frozenset({"cycling_mountain_biking", "winter_biking", "bike_rental"})
# openingHours[].weekday values -> Finnish abbreviations, in week order.
WEEKDAYS = {
    "monday": "ma",
    "tuesday": "ti",
    "wednesday": "ke",
    "thursday": "to",
    "friday": "pe",
    "saturday": "la",
    "sunday": "su",
}

PRODUCT_FIELDS = """
    id type updatedAt urlPrimary
    postalAddresses { city streetName postalCode location }
    productInformations { language name description url }
    productTags { tag }
    company { businessName websiteUrl }
    openingHours { weekday opens closes open }"""


class SourceError(Exception):
    """Missing settings or an answer the source refused; the message is shown to the editor."""


def api_settings() -> tuple[str, str]:
    """(url, key) from the environment; VF_API_KEY is required, VF_API_URL has a default."""
    key = env("VF_API_KEY")
    if not key:
        raise SourceError(
            "VF_API_KEY missing: set the Business Finland API portal subscription key in .env"
        )
    return env("VF_API_URL", VF_API_URL) or VF_API_URL, key


def query(city: str, limit: int = PAGE_SIZE, offset: int = 0) -> str:
    """GraphQL query for one page of products whose postal address is in `city`."""
    where = f"{{postalAddresses: {{city: {{_ilike: {json.dumps(city)}}}}}}}"
    return f"{{ product(limit: {limit}, offset: {offset}, where: {where}) {{{PRODUCT_FIELDS} }} }}"


def _page(city: str, offset: int, url: str, key: str, timeout_s: int) -> list[dict]:
    request = urllib.request.Request(
        url,
        data=json.dumps({"query": query(city, PAGE_SIZE, offset)}).encode("utf-8"),
        headers={"ocp-apim-subscription-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_s, context=ssl_context()) as response:
        answer = json.load(response)
    if answer.get("errors"):
        messages = "; ".join(str(e.get("message", e)) for e in answer["errors"])
        raise SourceError(f"Visit Finland DataHub: {messages}")
    return answer["data"]["product"]


def fetch(city: str, *, url: str = VF_API_URL, key: str, timeout_s: int = 120) -> list[dict]:
    """Raw products of every page; pagination stops at the first page shorter than PAGE_SIZE."""
    products: list[dict] = []
    offset = 0
    while True:
        page = _page(city, offset, url, key, timeout_s)
        products += page
        if len(page) < PAGE_SIZE:
            return products
        offset += PAGE_SIZE


def category(product: dict) -> str | None:
    """Category of the type table, or None when the product is not a service point."""
    kind = product.get("type")
    if kind == "rental_service":
        tags = {t.get("tag") for t in product.get("productTags") or []}
        return "bike_rental" if tags & BIKE_RENTAL_TAGS else None
    return TYPE_CATEGORIES.get(kind)


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _location(product: dict) -> tuple[float, float] | None:
    """(lon, lat) of the first address with a location; DataHub serves "(lat,lon)"."""
    for address in product.get("postalAddresses") or []:
        text = _text(address.get("location"))
        if text:
            lat, lon = (float(v) for v in text.strip("()").split(","))
            return (round(lon, 6), round(lat, 6))
    return None


def _clock(value: object) -> str | None:
    """ "10:00:00" -> "10", "10:30:00" -> "10:30"; None when missing."""
    text = _text(value)
    if not text:
        return None
    hours, minutes, *_ = text.split(":")
    return hours if minutes == "00" else f"{hours}:{minutes}"


def opening_hours(hours: list[dict] | None) -> str | None:
    """Compact text "ma–pe 10–18; la 10–14": days in week order, equal consecutive days merged,
    days without times or marked closed left out (P11)."""
    by_day: dict[str, str] = {}
    for entry in hours or []:
        opens, closes = _clock(entry.get("opens")), _clock(entry.get("closes"))
        if entry.get("open", True) and opens and closes and entry.get("weekday") in WEEKDAYS:
            by_day[entry["weekday"]] = f"{opens}–{closes}"
    runs: list[list[str]] = []  # [first day, last day, times]
    for index, day in enumerate(WEEKDAYS):
        times = by_day.get(day)
        if times is None:
            continue
        previous = list(WEEKDAYS)[index - 1] if index else None
        if runs and runs[-1][1] == previous and runs[-1][2] == times:
            runs[-1][1] = day
        else:
            runs.append([day, day, times])
    parts = [
        f"{WEEKDAYS[first]}{'–' + WEEKDAYS[last] if last != first else ''} {times}"
        for first, last, times in runs
    ]
    return "; ".join(parts) or None


def _lang_text(product: dict, key: str, limit: int | None = None) -> dict[str, str] | None:
    result = {}
    for info in product.get("productInformations") or []:
        language, text = info.get("language"), _text(info.get(key))
        if isinstance(language, str) and len(language) == 2 and text:
            result[language] = text[:limit] if limit else text
    return result or None


def _url(product: dict) -> str | None:
    english = next(
        (i for i in product.get("productInformations") or [] if i.get("language") == "en"), {}
    )
    return (
        _text(english.get("url"))
        or _text(product.get("urlPrimary"))
        or _text((product.get("company") or {}).get("websiteUrl"))
    )


def _service(product: dict, fetched_at: str) -> Service | None:
    kind = category(product)
    location = _location(product) if kind else None
    if kind is None or location is None:
        return None
    return Service(
        id=f"vf:{product['id']}",
        name=_lang_text(product, "name"),
        category=kind,
        source="visitfinland",
        url=_url(product),
        opening_hours=opening_hours(product.get("openingHours")),
        description=_lang_text(product, "description", DESCRIPTION_MAX),
        fetched_at=fetched_at,
        location=location,
    )


def parse(products: list[dict], fetched_at: str | None = None) -> list[Service]:
    """Products → services of the type table, sorted by id. Products without a category or a
    location are left out."""
    fetched_at = fetched_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    services = (_service(p, fetched_at) for p in products)
    return sorted((s for s in services if s is not None), key=lambda s: s.id)


def snapshot_path(data_dir: Path) -> Path:
    return data_dir / "services" / "visitfinland.geojson"


def write_snapshot(data_dir: Path, services: list[Service]) -> Path:
    path = snapshot_path(data_dir)
    write_json(path, services_collection(services))
    return path


def read_snapshot(data_dir: Path) -> list[Service]:
    """The services of services/visitfinland.geojson; empty without a snapshot."""
    return read_features(snapshot_path(data_dir), Service)
