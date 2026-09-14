"""HTTP helpers shared by the importers and the tile fetcher."""

import functools
import ssl


@functools.cache
def ssl_context() -> ssl.SSLContext:
    """certifi's CA bundle when available (it ships with pyproj): the uv-managed Python build's
    default bundle rejects some Finnish certificate chains (MML, Telia)."""
    try:
        import certifi
    except ImportError:  # pragma: no cover
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())
