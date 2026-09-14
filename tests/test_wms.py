"""WMS capabilities (5.4, wms_external): named layers of a saved 1.1.1 document. Offline."""

from pathlib import Path

import pytest

from manager.sources import wms

SAMPLE = Path(__file__).parent / "fixtures" / "wms" / "capabilities_sample.xml"
URL = "https://rovaniemi.asiointi.fi/teklaogcweb/WMS.ashx"


def test_parse_lists_named_layers_and_skips_groups():
    layers = wms.parse(SAMPLE.read_bytes())
    assert [layer.name for layer in layers] == ["Ilmakuva 2025", "Opaskartta_qgs", "Pohjakartta"]
    assert layers[1].title == "Opaskartta_qgs"
    assert layers[1].bbox == (24.679804, 66.15354, 27.309355, 67.17782)


@pytest.mark.parametrize("xml", [b"<html>not wms</html>", b"<x", b""])
def test_parse_rejects_non_capabilities(xml):
    with pytest.raises(ValueError, match="not a capabilities document"):
        wms.parse(xml)


def test_parse_layer_without_bbox():
    xml = b"<WMT_MS_Capabilities><Capability><Layer><Name>a</Name></Layer></Capability></WMT_MS_Capabilities>"
    assert wms.parse(xml) == [wms.WmsLayer(name="a", title="a", bbox=None)]


def test_capabilities_url_keeps_existing_query():
    assert wms.capabilities_url(URL) == (f"{URL}?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1")
    assert wms.capabilities_url(f"{URL}?map=a&SERVICE=x") == (
        f"{URL}?map=a&SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1"
    )


def test_capabilities_fetches_with_user_agent(monkeypatch):
    seen = {}

    class Response:
        def __init__(self, request):
            seen["url"] = request.full_url
            seen["agent"] = request.get_header("User-agent")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return SAMPLE.read_bytes()

    monkeypatch.setattr(wms.urllib.request, "urlopen", lambda request, timeout: Response(request))
    assert [layer.name for layer in wms.capabilities(URL)][:1] == ["Ilmakuva 2025"]
    assert seen["url"] == wms.capabilities_url(URL) and seen["agent"] == "hubandcircles-manager"
