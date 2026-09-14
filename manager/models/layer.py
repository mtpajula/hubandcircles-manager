"""Layer card (layers/<id>.json), chapter 5.4.

Two sides: `source` and `publish_format` tell the tool how to obtain and publish the data and
stay out of the published card; the rest tells the frontend how to draw the layer.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from manager.models.common import LangText
from manager.models.identifiers import LayerSlot, LayerType, ServiceCategory


class LegendEntry(BaseModel):
    """One row of a raster legend (5.4): the colour and its label."""

    model_config = ConfigDict(extra="forbid")

    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    label: LangText


class RasterClass(LegendEntry):
    """A class of a classified GeoTIFF: the legend row plus the pixel value."""

    value: int


class WmsExternalSource(BaseModel):
    """External keyless WMS the browser calls directly; `url` and `wms` are on the card."""

    model_config = ConfigDict(extra="forbid")

    method: Literal["wms_external"]


class XyzExternalSource(BaseModel):
    """External raster tiles; the `{z}/{x}/{y}` template is `url` on the card."""

    model_config = ConfigDict(extra="forbid")

    method: Literal["xyz_external"]


class ServicesSource(BaseModel):
    """Merged service points of these categories as one GeoJSON (7.2, service layers)."""

    model_config = ConfigDict(extra="forbid")

    method: Literal["services"]
    categories: list[ServiceCategory] = Field(min_length=1)


class GeojsonFileSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["geojson_file"]
    file: str  # relative to the data directory


class TileDirSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["tile_dir"]
    dir: str  # under TILE_CACHE_DIR, XYZ layout


class MmlCorridorSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["mml_corridor"]
    layer: str  # WMTS layer name, e.g. `maastokartta`
    buffers_m: dict[str, int]  # zoom level -> corridor half-width in metres (7.3)
    # Published under layers/<id>/v<version>/ (7.5); bump by hand when the map changes.
    version: int = Field(default=1, ge=1)


class GeotiffSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["geotiff"]
    file: str  # relative to SOURCE_FILES_DIR
    classes: list[RasterClass] = Field(min_length=1)


LayerSource = Annotated[
    WmsExternalSource
    | XyzExternalSource
    | ServicesSource
    | GeojsonFileSource
    | TileDirSource
    | MmlCorridorSource
    | GeotiffSource,
    Field(discriminator="method"),
]

# Source methods the build publishes today; the others are accepted and skipped with a warning.
# ponytail: tile_dir and geotiff arrive with the GeoTIFF tiler (7.4).
BUILT_METHODS = frozenset(
    {"wms_external", "xyz_external", "services", "geojson_file", "mml_corridor"}
)


class VisibleIn(BaseModel):
    """Where the layer is offered (5.4): every theme or the listed ones, plus open routes."""

    model_config = ConfigDict(extra="forbid")

    themes: Literal["*"] | list[str] = "*"
    routes: list[str] = []


class Wms(BaseModel):
    """GetMap parameters of a `wms` layer."""

    model_config = ConfigDict(extra="forbid")

    version: str = "1.1.1"
    layers: str
    format: str = "image/png"
    srs: str = "EPSG:3857"


class VectorStyle(BaseModel):
    """Simplified vector style (5.4); the frontend adapter turns it into MapLibre paint."""

    model_config = ConfigDict(extra="forbid")

    color: str | None = None
    width: float | None = None
    dashed: bool | None = None
    icon: str | None = None
    opacity: float | None = None


class Layer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: LangText
    slot: LayerSlot
    source: LayerSource
    publish_format: LayerType | None = None
    visible_in: VisibleIn = VisibleIn()
    default_on: bool = False
    minzoom: int | None = None
    maxzoom: int | None = None
    opacity: float | None = Field(default=None, ge=0, le=1)
    attribution: str
    url: str | None = None  # wms_external: service address; xyz_external: tile template
    wms: Wms | None = None
    style: VectorStyle | None = None
    maplibre: dict | None = None  # escape hatch, passed through as is (5.4)

    @model_validator(mode="after")
    def _external_sources_need_url(self) -> "Layer":
        method = self.source.method
        if method in ("wms_external", "xyz_external") and not self.url:
            raise ValueError(f"source method {method} needs url")
        if method == "wms_external" and self.wms is None:
            raise ValueError("source method wms_external needs wms")
        return self
