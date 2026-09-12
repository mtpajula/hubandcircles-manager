"""Header rules → Cloudflare _headers; the file is created only with a cloudflare target."""

from manager.models import Target
from manager.models.publish_settings import defaults
from manager.publish.bundle import assemble
from manager.publish.headers import cloudflare_headers


def _blocks(text: str) -> dict[str, list[str]]:
    return {
        block.splitlines()[0]: [line.strip() for line in block.splitlines()[1:]]
        for block in text.strip().split("\n\n")
    }


def test_cloudflare_headers():
    blocks = _blocks(cloudflare_headers(defaults().headers))
    assert blocks["/data/catalog.json"] == ["Cache-Control: public, max-age=300"]
    assert blocks["/data/**/*.pmtiles"] == [
        "Cache-Control: public, max-age=31536000, immutable",
        "Content-Type: application/vnd.pmtiles",
    ]
    assert blocks["/data/**/*.gpx"] == [
        "Cache-Control: public, max-age=300",
        "Content-Type: application/gpx+xml",
    ]
    assert blocks["/index.html"] == ["Cache-Control: no-cache"]
    assert len(blocks) == 8


def test_headers_only_with_cloudflare_target(frontend, dist, tmp_path):
    without = defaults()
    without.targets = [Target(id="x", type="github-pages", repo="a/b")]
    assert not (assemble(frontend, dist, without, tmp_path / "b1").directory / "_headers").exists()

    cf = defaults()
    cf.targets = [Target(id="primary", type="cloudflare-pages", project="hc")]
    headers = assemble(frontend, dist, cf, tmp_path / "b2").directory / "_headers"
    assert headers.read_text() == cloudflare_headers(cf.headers)
