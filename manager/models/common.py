"""Types shared by all models."""

from typing import Annotated

from pydantic import Field

# User-visible text per language, e.g. {"fi": "...", "en": "..."}.
# The default language being present is checked in the validate stage, not in the model.
LangText = Annotated[dict[str, str], Field(min_length=1)]

# lon_min, lat_min, lon_max, lat_max
Bbox = tuple[float, float, float, float]
