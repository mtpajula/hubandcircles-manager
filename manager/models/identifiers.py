"""Fixed identifiers (chapter 5.7). Adding a value is a tech-lead decision, not a data change.

Each Literal is the type used in the models; the matching tuple is for UI option lists and
checks. `unknown` (surface, traffic) and `mixed` (dominant surface) are derived in the build
and never appear in source data.
"""

from typing import Literal, get_args

KeyFigure = Literal[
    "length",
    "ascent",
    "difficulty",
    "itrs_technical",
    "itrs_endurance",
    "itrs_exposure",
    "itrs_wilderness",
    "dominant_surface",
    "surface_shares",
    "separated_share",
    "winter_maintenance",
    "longest_service_gap",
]
BandLane = Literal["elevation", "surface", "traffic", "itrs_technical"]
HeroImage = Literal["cover_image", "hardest_section"]
FilterId = Literal[
    "length",
    "ascent",
    "difficulty",
    "itrs_technical",
    "dominant_surface",
    "separated_share",
    "winter_maintenance",
]
ItrsLevel = Literal["green", "blue", "red", "black", "orange"]
Surface = Literal["asphalt", "paving", "gravel", "trail", "boardwalk", "snow"]
Traffic = Literal["separated", "quiet", "busy"]
WinterMaintenance = Literal["plowed", "groomed", "none"]
Difficulty = Literal["easy", "moderate", "demanding"]
Season = Literal["spring", "summer", "autumn", "winter"]
# Being in the municipal register (Lipas) is the definition of "municipal" (5.3, AP24).
Maintainer = Literal["municipal", "non_municipal"]
NonMunicipalReason = Literal[
    "private_road_no_permission",
    "unmarked",
    "unmaintained",
    "everymans_rights_terrain",
    "seasonal",
]
SectionType = Literal["text", "gallery", "video", "elevation_profile"]
# Where the track's elevations come from: the uploaded file, or the MML 2 m DEM fill (AP40).
ElevationSource = Literal["gpx", "geojson", "mml_dem"]
# Service point categories (5.5); `issue` is a problem spot with severity and validity.
ServiceCategory = Literal[
    "cafe",
    "restaurant",
    "shop",
    "accommodation",
    "bike_repair",
    "bike_rental",
    "water",
    "toilet",
    "lean_to",
    "hut",
    "issue",
]
# Merge priority in build/services.py: manual > visitfinland > osm (5.5).
ServiceSource = Literal["osm", "visitfinland", "manual"]
# Severity of an `issue` point (5.5): the frontend picks the marker style from it.
IssueSeverity = Literal["info", "warning", "danger"]
# Map layer slots (5.7, chapter 8): fixed in the frontend, chosen per layer card.
LayerSlot = Literal["base", "raster", "area", "routes", "points"]
# Published layer types (5.4): each is frontend code; the build derives them from the source.
LayerType = Literal["xyz", "pmtiles", "geojson", "wms"]

KEY_FIGURES: tuple[str, ...] = get_args(KeyFigure)
BAND_LANES: tuple[str, ...] = get_args(BandLane)
HERO_IMAGES: tuple[str, ...] = get_args(HeroImage)
FILTER_IDS: tuple[str, ...] = get_args(FilterId)
ITRS_LEVELS: tuple[str, ...] = get_args(ItrsLevel)
SURFACES: tuple[str, ...] = get_args(Surface)
TRAFFICS: tuple[str, ...] = get_args(Traffic)
WINTER_MAINTENANCES: tuple[str, ...] = get_args(WinterMaintenance)
DIFFICULTIES: tuple[str, ...] = get_args(Difficulty)
SEASONS: tuple[str, ...] = get_args(Season)
MAINTAINERS: tuple[str, ...] = get_args(Maintainer)
NON_MUNICIPAL_REASONS: tuple[str, ...] = get_args(NonMunicipalReason)
SECTION_TYPES: tuple[str, ...] = get_args(SectionType)
SERVICE_CATEGORIES: tuple[str, ...] = get_args(ServiceCategory)
SERVICE_SOURCES: tuple[str, ...] = get_args(ServiceSource)
ISSUE_SEVERITIES: tuple[str, ...] = get_args(IssueSeverity)
LAYER_SLOTS: tuple[str, ...] = get_args(LayerSlot)
LAYER_TYPES: tuple[str, ...] = get_args(LayerType)

# Level number shown next to the name and colour (5.3): green 1 ... orange 5.
ITRS_LEVEL_NUMBER = {level: number for number, level in enumerate(ITRS_LEVELS, start=1)}

# At most this many band lanes besides `elevation` (5.7).
MAX_BAND_LANES = 3
