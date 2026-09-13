"""Theme (themes/<id>.json), chapter 5.2."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from manager.models.common import LangText
from manager.models.identifiers import MAX_BAND_LANES, BandLane, FilterId, HeroImage, KeyFigure

COLOR = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class Colors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str = COLOR
    route: str = COLOR
    highlight: str = COLOR


class Presentation(BaseModel):
    """Which route facts come first in this theme (5.2). Lists hold 5.7 identifiers only,
    in display order; the frontend falls back to length, ascent, elevation and cover image."""

    model_config = ConfigDict(extra="forbid")

    key_figures: list[KeyFigure] = []
    band: list[BandLane] = []
    hero_image: HeroImage = "cover_image"
    filters: list[FilterId] = []
    service_categories_first: list[str] = []  # service categories (5.5), free until V3

    @field_validator("band")
    @classmethod
    def _at_most_three_lanes(cls, band: list[str]) -> list[str]:
        if len([lane for lane in band if lane != "elevation"]) > MAX_BAND_LANES:
            raise ValueError(f"band has more than {MAX_BAND_LANES} lanes besides elevation")
        return band


class Theme(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: LangText
    tagline: LangText | None = None
    order: int
    icon: str | None = None
    colors: Colors
    dark: bool = False
    basemap: str | None = None
    default_layers: list[str] = []
    presentation: Presentation | None = None
