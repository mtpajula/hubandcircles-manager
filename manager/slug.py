"""Slugs: the tool owns names and paths (P6), so route ids and media file names come from here."""

import re
import unicodedata

MAX_ID_LENGTH = 60


def slugify(text: str) -> str:
    """ASCII slug: accents stripped, non-alphanumerics collapsed to '-', at most 60 chars."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:MAX_ID_LENGTH].rstrip("-")
