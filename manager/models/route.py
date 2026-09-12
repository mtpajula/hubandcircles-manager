"""Route card, source data (routes/<id>/route.json), chapter 5.3."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from manager.models.common import LangText


class TextSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["text"]
    content: LangText


class GallerySection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["gallery"]
    media: list[str]


class VideoSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["video"]
    url: str


class ElevationProfileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["elevation_profile"]


Section = Annotated[
    TextSection | GallerySection | VideoSection | ElevationProfileSection,
    Field(discriminator="type"),
]


# Being in the municipal register (Lipas) is the definition of "municipal" (5.3, AP24).
Maintainer = Literal["municipal", "non_municipal"]


class MediaInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    author: str
    license: str


class Route(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: LangText
    themes: list[str]
    seasons: list[str]
    # ponytail: free string in V1; Literal["easy", "moderate", "demanding"] in V2.
    # None = not assessed (P11); an imported route starts without one.
    difficulty: str | None = None
    track: str = "track.gpx"
    cover_image: str | None = None
    sections: list[Section] = []
    media: dict[str, MediaInfo] = {}
    lipas_id: int | None = None  # Lipas sports facility id (properties.id), chapter 7.13
    maintainer: Maintainer | None = None  # None = unknown, no marker shown (AP24)
