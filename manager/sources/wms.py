"""WMS GetCapabilities: the layer names an external service offers (5.4, wms_external).

fetch() is the only function that touches the network; parse() is pure and tested against a
saved answer. The Streamlit layers page offers the names in a selectbox.
"""

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from manager.http import ssl_context
from manager.models import Bbox

USER_AGENT = "hubandcircles-manager"
CAPABILITIES_QUERY = {"SERVICE": "WMS", "REQUEST": "GetCapabilities", "VERSION": "1.1.1"}


@dataclass
class WmsLayer:
    name: str
    title: str
    bbox: Bbox | None  # WGS84 lon/lat from LatLonBoundingBox; None when the layer has none


def capabilities_url(url: str) -> str:
    """The service address with the GetCapabilities query, keeping any existing parameters."""
    parts = urllib.parse.urlsplit(url)
    query = dict(urllib.parse.parse_qsl(parts.query))
    query.update(CAPABILITIES_QUERY)
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def fetch(url: str, *, timeout_s: int = 30) -> bytes:
    """Raw GetCapabilities XML of the service."""
    request = urllib.request.Request(capabilities_url(url), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_s, context=ssl_context()) as response:
        return response.read()


def _bbox(element: ET.Element) -> Bbox | None:
    box = element.find("LatLonBoundingBox")
    if box is None:
        return None
    try:
        return tuple(float(box.attrib[k]) for k in ("minx", "miny", "maxx", "maxy"))
    except (KeyError, ValueError):
        return None


def parse(xml: bytes) -> list[WmsLayer]:
    """Every named layer of a WMS 1.1.1 capabilities document, in document order.

    Group layers (Title without Name) are containers and are skipped; ValueError on bad XML."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise ValueError(f"not a capabilities document: {e}") from e
    if root.find("Capability") is None:
        raise ValueError("not a capabilities document: no Capability element")
    layers = []
    for element in root.iter("Layer"):
        name = element.findtext("Name")
        if name:
            title = element.findtext("Title") or name
            layers.append(WmsLayer(name=name, title=title, bbox=_bbox(element)))
    return layers


def capabilities(url: str, *, timeout_s: int = 30) -> list[WmsLayer]:
    """fetch() + parse(): the named layers of the service at `url`."""
    return parse(fetch(url, timeout_s=timeout_s))
