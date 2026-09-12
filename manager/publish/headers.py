"""Translate header rules into the target's format (chapter 12.6). New target = new function."""

from manager.models import HeaderRule

CACHE_CONTROL = {
    "immutable": "public, max-age=31536000, immutable",
    "short": "public, max-age=300",
    "none": "no-cache",
}


def cloudflare_headers(rules: list[HeaderRule]) -> str:
    """Cloudflare Pages `_headers`: a path line followed by indented headers, per block."""
    # ponytail: paths are written as-is; glob dialect (`**`) compatibility is confirmed
    # by a host check in V4.
    blocks = []
    for rule in rules:
        lines = [rule.path, f"  Cache-Control: {CACHE_CONTROL[rule.cache]}"]
        if rule.content_type:
            lines.append(f"  Content-Type: {rule.content_type}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"
