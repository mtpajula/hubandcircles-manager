"""Theme (themes/<id>.json), chapter 5.2."""

from pydantic import BaseModel, ConfigDict, Field

from manager.models.common import LangText

COLOR = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class Colors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str = COLOR
    route: str = COLOR
    highlight: str = COLOR


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
    # ponytail: `presentation` (5.2) is added in V2.
