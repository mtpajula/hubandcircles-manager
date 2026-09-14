"""Every user-visible string of the Streamlit UI. Finnish by design (ADMIN-UI-SPEC intro).

The only module in the package where Finnish prose is allowed; identifiers stay English (P10).
"""

APP_TITLE = "Napa ja piirit"
APP_SUBTITLE = "hallintatyökalu"

PAGE_ROUTES = "Reitit"
PAGE_LAYERS = "Tasot"
PAGE_SERVICES = "Palvelut"
PAGE_REPORTS = "Ilmoitukset"
PAGE_THEMES = "Teemat"
PAGE_BUILD_PUBLISH = "Build ja julkaisu"

COMING_V3 = "Tulee vaiheessa V3."
COMING_V5 = "Tulee vaiheessa V5."
COMING_V6 = "Tulee vaiheessa V6."

# Sidebar footer: source data status
SIDEBAR_SOURCE_DATA = "Lähdedata"
SIDEBAR_CHANGES = "{count} muutosta commitoimatta"
SIDEBAR_BRANCH_AHEAD = "haara {branch} · {ahead} commitia pushaamatta"
SIDEBAR_NOT_A_REPO = "Ei git-repositorio"
SIDEBAR_LAST_PUBLISH = "Viimeisin julkaisu {when}"
SIDEBAR_NO_PUBLISH = "Ei vielä julkaistu"

DATA_DIR_MISSING = "Lähdedata puuttuu: aseta DATA_DIR .env-tiedostoon."
CLI_EQUIVALENT = "Komentorivillä: `{command}`"

# Build & publish page (ADMIN-UI-SPEC section 7)
BUILD_PUBLISH_INTRO = (
    "Muutokset syntyvät Reitit- ja Teemat-sivuilla lähdedataan (`hubandcircles-data`). Build tekee "
    "niistä julkaisudatan, esikatselu näyttää sen sivuston kanssa, ja julkaisu vie paketin "
    "sivustolle ja lähdedatan GitHubiin."
)
BUILD_FIRST = "Aja build ensin"

STEP_BUILD_HEADER = "1 · Build"
STEP_BUILD_INTRO = (
    "Lähdedata → julkaisudata (`dist/`). Tarkistaa skeeman, linkit, viittaukset, käännökset ja "
    "avainvuodot; virhe pysäyttää."
)
BUTTON_BUILD = "Aja build"
BUILD_RUNNING = "Build käynnissä…"
BUILD_DONE = "Build valmis"
BUILD_FAILED = "Build keskeytyi, dist/ ennallaan"
BUILD_FINISHED_AT = "Valmistui {time} · {seconds} s"
BUILD_PREVIOUS = "Edellinen build {when}"
METRIC_ROUTES = "Reittejä"
METRIC_FIRST_VISIT = "Ensikäynti"
METRIC_WARNINGS = "Varoituksia"
CHECKS_HEADER = "Tarkistukset"
CHECK_NAMES = {
    "schema": "Skeema",
    "enums": "Enum-arvot",
    "links": "Linkit",
    "references": "Viittaukset",
    "layers": "Tasot",
    "presentation": "Esitystunnisteet",
    "segments": "Segmentit",
    "hardest_section": "Vaativin kohta",
    "media": "Kuvien tiedot",
    "itrs_values": "ITRS-luvut",
    "maintenance_reasons": "Ylläpitosyyt",
    "translations": "Käännökset",
    "manual_markers": "Käsin tehdyt merkinnät",
    "itrs_missing": "ITRS puuttuu",
    "segment_coverage": "Segmenttikattavuus",
    "normalisation": "Normalisointi",
    "secrets": "Avainvuodot",
    "theme_contrast": "Teemavärien kontrasti",
}
CHECK_PASSED = "✓ {name}"
CHECK_WARNING = "! {name} · {count} varoitusta"
CHECK_INFO = "i {name} · {count} tietoa"
CHECK_SHOW = "Näytä"

COVERAGE_HEADER = "Esitystavan kattavuus teemoittain"
COVERAGE_COLUMNS = {"theme": "teema", "slot": "kohta", "item": "tieto", "routes": "reittejä"}
COVERAGE_SLOT_NAMES = {"key_figures": "avainluku", "band": "nauha"}
COVERAGE_ROUTES = "{with_data} / {routes} reittiä"

STEP_PREVIEW_HEADER = "2 · Esikatselu"
STEP_PREVIEW_INTRO = (
    "Näyttää julkaisudatan yhdessä frontend-buildin kanssa paikallisesti; tämä on täsmälleen se "
    "paketti, joka julkaistaan."
)
BUTTON_PREVIEW = "Käynnistä esikatselu"
BUTTON_PREVIEW_OPEN = "Avaa esikatselu"
BUTTON_PREVIEW_STOP = "Pysäytä esikatselu"
PREVIEW_STOPPED = "Esikatselu pysäytetty."
PREVIEW_FAILED = "Esikatselu keskeytyi."
PREVIEW_KEEPS_RUNNING = "Esikatselu jää käyntiin kunnes pysäytät sen tai suljet Streamlitin."
FRONTEND_MISSING = "Buildaa frontend: `cd hubandcircles-ui && npm run build`"

STEP_PUBLISH_HEADER = "3 · Julkaise"
STEP_PUBLISH_INTRO = (
    "Vie paketin (frontend + `data/`) julkaisukohteisiin ja tallentaa lähdedatan GitHubiin, jotta "
    "sivusto ja data ovat samassa tilassa."
)
FRONTEND_CAPTION = "Frontend: {frontend}"
FRONTEND_PINNED = "{repo} v{version} (kiinnitetty publish.json-tiedostossa)"
NO_TARGETS = "Ei julkaisukohteita"
SOURCE_REPO_STATUS = (
    "Lähdedata: {name} · haara {branch} · {changed} muutosta commitoimatta · {ahead} pushaamatta"
)
SOURCE_REPO_CLEAN = "Lähdedata on jo GitHubissa"
SAVE_SOURCE_DATA = "Tallenna lähdedata GitHubiin (commit + push)"
COMMIT_MESSAGE_LABEL = "Commit-viesti"
COMMIT_MESSAGE_DEFAULT = "Update route data"
BUTTON_PUBLISH = "Julkaise"
PUBLISH_RUNNING = "Julkaisu käynnissä…"
PUBLISH_DONE = "Julkaisu valmis"
PUBLISH_FAILED = "Julkaisu keskeytyi"
PUBLISH_BUNDLE_LINE = "Paketti koottu: {files} tiedostoa, {mib} MiB"
PUBLISH_SOURCE_LINE = "Lähdedata: {sha} pushattu"
PUBLISH_SOURCE_NOTHING = "Lähdedata: ei muutoksia"
PUBLISHED_AT = "Julkaistu {time}"
BUTTON_OPEN_SITE = "Avaa sivusto"
PAGES_UPDATES_SOON = "GitHub Pages päivittyy noin minuutissa."
CLI_EQUIVALENT_BOTH = "Komentorivillä: `{first}` ja `{second}`"

# Shared
SOURCE_DATA_BROKEN = "Lähdedata ei kelpaa: {error}"
BUTTON_SAVE = "Tallenna"
SAVED = "Tallennettu: {path}"
SAVE_FAILED = "Tallennus epäonnistui: {error}"
LANGUAGE_NAMES = {"fi": "Suomi", "en": "English"}
MISSING_COUNT = "{count} puuttuu"
NONE_OPTION = "–"

# Routes page
ROUTE_SELECT = "Reitti"
ROUTE_NEW = "Uusi reitti"
ROUTE_ID = "Tunniste"
ROUTE_ID_HELP = "Kansion nimi routes/-hakemistossa: pieniä kirjaimia, numeroita ja viivoja."
ROUTE_NAME = "Nimi"
ROUTE_DESCRIPTION = "Kuvaus"
ROUTE_THEMES = "Teemat"
ROUTE_SEASONS = "Kaudet"
SEASON_NAMES = {"summer": "Kesä", "winter": "Talvi"}
ROUTE_DIFFICULTY = "Vaativuus"
DIFFICULTY_NAMES = {"easy": "helppo", "moderate": "keskivaativa", "demanding": "vaativa"}
ROUTE_MAINTAINER = "Ylläpito"
MAINTAINER_NAMES = {"municipal": "kunnan ylläpitämä", "non_municipal": "ei kunnan ylläpitämä"}
MAINTAINER_UNKNOWN = "ei tietoa"
MAINTAINER_SHORT = {"municipal": "kunta", "non_municipal": "ei kunnan"}
REASON_COUNT = "{count} syytä"
ROUTE_LIPAS_ID = "Lipas-tunnus"
ROUTE_LIPAS_ID_HELP = "0 = ei kytkentää"
ROUTE_GPX = "GPX-jälki"
ROUTE_GPX_KEEP = "Tyhjä = nykyinen jälki säilyy."
BUTTON_SAVE_ROUTE = "Tallenna reitti"
BUTTON_DELETE_ROUTE = "Poista reitti"
CONFIRM_DELETE = "Vahvista poisto"
DELETE_UNCONFIRMED = 'Rastita ensin "Vahvista poisto".'
ROUTE_SAVED = "Reitti tallennettu: {path}"
ROUTE_DELETED = "Reitti poistettu: {route_id}"
ROUTE_CREATE_NEEDS_GPX = "Uusi reitti tarvitsee GPX-jäljen."
METRIC_LENGTH = "Pituus"
METRIC_ASCENT = "Nousu"
METRIC_IMAGES = "Kuvia"
NO_ELEVATIONS = "Jäljessä ei ole korkeuksia; nousu ja profiili jäävät pois (P11)."
NO_ROUTE_SELECTED = "Valitse reitti tai luo uusi."
TRACK_BROKEN = "Jälkeä ei voi lukea: {error}"
MAP_LATER = "Karttaesikatselu tulee vaiheessa V2."
ROUTES_TABLE_HEADER = "Reitit"
ROUTES_TABLE_COLUMNS = {
    "name": "nimi",
    "themes": "teemat",
    "translation": "käännös",
    "maintainer": "ylläpito",
    "lipas_id": "lipas",
}
SIDEBAR_CURRENT_ROUTE = "Reitti: {name} · {themes}"

ITRS_SUMMARY = "ITRS ja vaativin kohta: {itrs} · vaativin kohta {hardest} — muokkaa alla"
ITRS_SUMMARY_NONE = "ei arvioitu"
HARDEST_SUMMARY_KM = "km {km}"
HARDEST_SUMMARY_NONE = "ei valittu"

# Images expander (2.1 dropzone, 5.3 media)
IMAGES_HEADER = "Kuvat"
IMAGES_UPLOAD = "Raahaa kuvat tähän"
IMAGES_UPLOAD_HINT = "Alkuperäiset kuvat suoraan kamerasta, jotta EXIF-sijainnit säilyvät."
IMAGE_AUTHOR = "Kuvaaja"
IMAGE_LICENSE = "Lisenssi"
IMAGE_LICENSE_DEFAULT = "CC BY 4.0"
IMAGE_IN_GALLERY = "galleriassa"
IMAGE_REMOVE = "poista"
IMAGE_FILE_MISSING = "tiedosto puuttuu"
IMAGES_NONE = "Reitillä ei ole vielä kuvia."
IMAGES_NEW_HEADER = "Uudet kuvat"
COVER_IMAGE = "Kansikuva"
BUTTON_SAVE_IMAGES = "Tallenna kuvat"
IMAGES_SAVED = "Kuvat tallennettu: {count} kuvaa"
IMAGE_INFO_MISSING = "Kuvaaja ja lisenssi puuttuvat: {key}"

# ITRS expander (2.4)
ITRS_HEADER = "ITRS-arvio"
ITRS_TECHNICAL = "Tekninen vaikeus"
ITRS_ENDURANCE = "Kestävyys"
ITRS_EXPOSURE = "Altistus"
ITRS_WILDERNESS = "Erämaisuus"
ITRS_ZERO_IS_NONE = "0 = ei arvoa"
ITRS_LEVEL_NAMES = {
    "green": "1 vihreä",
    "blue": "2 sininen",
    "red": "3 punainen",
    "black": "4 musta",
    "orange": "5 oranssi",
}
ITRS_LEVELS_CAPTION = "Tasot: " + " · ".join(ITRS_LEVEL_NAMES.values())
ITRS_ASSESSED_BY = "Arvioija"
ITRS_ASSESSED_ON = "Arvioitu"
ITRS_SCALE_UNLOCKED = (
    "Asteikkoa ei ole lukittu: altistus ja erämaisuus validoidaan vain positiivisina "
    "kokonaislukuina, kunnes ITRS-oppaan tasot on tarkistettu."
)
BUTTON_SAVE_ITRS = "Tallenna ITRS-arvio"
ITRS_SAVED = "ITRS-arvio tallennettu."

# Hardest section expander (2.5)
HARDEST_HEADER = "Vaativin kohta"
HARDEST_MEDIA = "Kuva"
HARDEST_KM = "Km"
HARDEST_KM_FROM_EXIF = "Km laskettu kuvan EXIF-sijainnista projisoimalla. Voit korjata arvon."
HARDEST_KM_NO_EXIF = "Kuvassa ei ole EXIF-sijaintia; anna km käsin."
HARDEST_DESCRIPTION = "Kuvaus"
HARDEST_NEEDS_IMAGES = "Lisää ensin kuva Kuvat-osiossa."
BUTTON_SAVE_HARDEST = "Tallenna vaativin kohta"
HARDEST_SAVED = "Vaativin kohta tallennettu."

# Segment editor (2.6)
SEGMENTS_HEADER = "Segmenttieditori"
SEGMENTS_COVERAGE = "kattavuus {percent} % · {unknown_km} km ilman tietoa"
SEGMENT_COLUMNS = {
    "start_km": "alku (km)",
    "end_km": "loppu (km)",
    "surface": "pinta",
    "traffic": "liikenne",
    "itrs_technical": "tekninen",
}
SURFACE_NAMES = {
    "asphalt": "asfaltti",
    "paving": "kiveys",
    "gravel": "sora",
    "trail": "polku",
    "boardwalk": "pitkospuut",
    "snow": "lumi",
}
TRAFFIC_NAMES = {"separated": "erotettu", "quiet": "hiljainen", "busy": "vilkas"}
SEGMENTS_PROBLEM = "Segmentit: {problem}"
SEGMENTS_INCOMPLETE_ROW = "Rivillä {row} alku tai loppu puuttuu."
SEGMENTS_MAP_CLICK_LATER = (
    "Rajan asettaminen karttaa klikkaamalla tulee karttaesikatselun mukana (V2b)."
)
BUTTON_SAVE_SEGMENTS = "Tallenna segmentit"
SEGMENTS_SAVED = "Segmentit tallennettu: {count} kpl"

# Maintenance expander (2.7)
MAINTENANCE_HEADER = "Ylläpito"
LIPAS_NO_LINK = "– ei kytkentää"
REASONS_HEADER = "Syyt · vähintään yksi"
REASON_NAMES = {
    "private_road_no_permission": "yksityistie, ei lupaa",
    "unmarked": "ei reittimerkintöjä",
    "unmaintained": "ei kunnossapitoa",
    "everymans_rights_terrain": "maastoliikennelaki",
    "seasonal": "kausiluonteinen",
}
MAINTENANCE_NOTE = "Tarkennus"
MAINTENANCE_NO_REASON = (
    "Validointi: ylläpito on non_municipal, mutta syytä ei ole valittu → virhe. Build pysähtyy, "
    "koska merkintä ilman perustelua on harhaanjohtava."
)
BUTTON_SAVE_MAINTENANCE = "Tallenna ylläpito"
MAINTENANCE_SAVED = "Ylläpito tallennettu."
LIPAS_SUGGESTION_LATER = "Lipas-ehdotus jäljen perusteella tulee vaiheessa V6."

LIPAS_HEADER = "Lipas"
LIPAS_SNAPSHOT_AT = "Tilannekuva haettu {when}"
LIPAS_NO_SNAPSHOT = "Ei tilannekuvaa"
BUTTON_LIPAS_FETCH = "Hae Lipasista"
LIPAS_FETCHING = "Haetaan Lipasista…"
LIPAS_FETCHED = "Lipas haettu: {count} reittiä"
LIPAS_FETCH_FAILED = "Lipas-haku epäonnistui"
BUTTON_LIPAS_CREATE = "Luo puuttuvat reittikansiot"
LIPAS_MATCHING_LATER = "Jäljen vertailu Lipas-reitteihin tulee vaiheessa V6."

# Services page (ADMIN-UI-SPEC section 4)
SERVICES_SNAPSHOT_AT = "Edellinen tilannekuva {when} · {count} pistettä"
SERVICES_NO_SNAPSHOT = "Ei tilannekuvaa"
OSM_LABELS = {
    "header": "OSM",
    "fetch": "Hae OSM:stä",
    "fetching": "Haetaan OSM:stä (Overpass)…",
    "fetched": "OSM haettu: {count} pistettä",
    "failed": "OSM-haku epäonnistui",
}
VF_LABELS = {
    "header": "Visit Finland",
    "fetch": "Hae Visit Finlandista",
    "fetching": "Haetaan Visit Finland DataHubista…",
    "fetched": "Visit Finland haettu: {count} pistettä",
    "failed": "Visit Finland -haku epäonnistui",
}
SERVICES_VF_KEY_MISSING = "Visit Finland -haku ei ole käytössä: VF_API_KEY puuttuu .env:stä."
SERVICES_VF_MUNICIPALITY_MISSING = (
    "Visit Finland -haku ei ole käytössä: project.json:sta puuttuu municipality."
)
METRIC_ADDED = "Uusia"
METRIC_REMOVED = "Poistuneita"
METRIC_CHANGED = "Muuttuneita"
METRIC_TOTAL = "Yhteensä"
CHANGES_HEADER = "Muutokset edelliseen tilannekuvaan"
CHANGE_COLUMNS = {"change": "muutos", "name": "nimi", "category": "kategoria", "id": "id"}
CHANGE_NAMES = {"added": "uusi", "removed": "poistui", "changed": "muuttui"}
NO_CHANGES = "Ei muutoksia edelliseen tilannekuvaan."
MANUAL_TARGET_MISSING = (
    "Käsin tehty korjaus kohteeseen {target} jäisi toimimattomaksi, jos tilannekuva hyväksytään."
)
BUTTON_ACCEPT_SNAPSHOT = "Hyväksy tilannekuva"
SNAPSHOT_ACCEPTED = "Tilannekuva tallennettu: {path}"
MANUAL_MARKERS_HEADER = "Käsin tehdyt merkinnät"
MANUAL_MARKERS_NONE = "Ei käsin tehtyjä merkintöjä."
MANUAL_MARKER_COLUMNS = {
    "id": "id",
    "name": "nimi",
    "category": "kategoria",
    "replaces": "korvaa",
    "hidden": "piilotettu",
}
MANUAL_MARKERS_MAP_LATER = (
    "Pisteiden lisäys kartalta tulee vaiheessa V3b; koordinaatit kirjoitetaan tai kopioidaan "
    "olemassa olevasta pisteestä."
)
MANUAL_NEW_HEADER = "Uusi piste"
MANUAL_NAME = "Nimi"
MANUAL_CATEGORY = "Kategoria"
MANUAL_LON = "Pituusaste (lon)"
MANUAL_LAT = "Leveysaste (lat)"
MANUAL_URL = "Verkko-osoite"
MANUAL_OPENING_HOURS = "Aukioloajat"
MANUAL_DESCRIPTION = "Kuvaus"
MANUAL_KEEP_HINT = "Tyhjä kenttä säilyttää alkuperäisen arvon."
BUTTON_SAVE_MARKER = "Tallenna piste"
MANUAL_NAME_REQUIRED = "Anna pisteelle nimi."
MANUAL_FIX_HEADER = "Korjaa tai piilota"
MANUAL_FIX_TARGET = "Palvelupiste"
MANUAL_FIX_NONE = "Ei palvelupisteitä: hae ensin tilannekuva."
MANUAL_HIDE = "Piilota"
BUTTON_SAVE_FIX = "Tallenna korjaus"
MANUAL_FIX_NO_CHANGES = "Ei muutettavaa: täytä kenttä tai rastita Piilota."
MANUAL_DELETE = "Poista merkintä"
BUTTON_DELETE_MARKER = "Poista"
MANUAL_SAVED = "Käsin tehdyt merkinnät tallennettu: {count} kpl ({path})"
RUN_BUILD_REMINDER = "Aja build, jotta muutos näkyy julkaisudatassa."
SERVICE_CATEGORY_NAMES = {
    "cafe": "kahvila",
    "restaurant": "ravintola",
    "shop": "kauppa",
    "accommodation": "majoitus",
    "bike_repair": "pyöräkorjaus",
    "bike_rental": "pyörävuokraus",
    "water": "juomavesi",
    "toilet": "wc",
    "lean_to": "laavu",
    "hut": "tupa",
    "issue": "ongelmakohta",
}

# Layers page (ADMIN-UI-SPEC section 3, simplified: external WMS/XYZ and service layers)
LAYERS_INTRO = (
    "Tasokortti kertoo työkalulle lähteen ja frontendille esitystavan. Teeman pohjakartta "
    "valitaan Teemat-sivulla base-paikan tasoista."
)
LAYERS_NONE = "Ei tasoja. Lisää WMS- tai XYZ-taso alla."
LAYER_COLUMNS = {
    "id": "taso",
    "name": "nimi",
    "slot": "paikka",
    "type": "muoto",
    "themes": "teemat",
    "default_on": "oletus",
}
LAYER_ON = "päällä"
LAYER_OFF = "pois"
LAYER_ALL_THEMES = "kaikki"
LAYER_TYPE_LATER = "ei vielä"
LAYER_EDIT_HEADER = "Muokkaa: {name}"
LAYER_ID = "Tunniste"
LAYER_ID_HELP = "Tiedoston nimi layers/-kansiossa: pieniä kirjaimia, numeroita ja viivoja."
LAYER_NAME = "Nimi"
LAYER_SLOT = "Paikka"
LAYER_SLOT_NAMES = {
    "base": "pohjakartta",
    "raster": "rasteri",
    "area": "alue",
    "routes": "reitit",
    "points": "pisteet",
}
LAYER_SOURCE = "Lähde"
LAYER_SOURCE_NAMES = {
    "wms_external": "ulkoinen WMS",
    "xyz_external": "ulkoiset XYZ-tiilet",
    "services": "palvelupisteet",
    "geojson_file": "GeoJSON-tiedosto",
    "tile_dir": "tiilikansio",
    "mml_corridor": "MML-käytävä",
    "geotiff": "GeoTIFF",
}
LAYER_VISIBILITY_HEADER = "Näkyvyys"
LAYER_ALL_THEMES_CHECKBOX = "Kaikissa teemoissa"
LAYER_THEMES = "Teemat"
LAYER_ROUTES = "Lisäksi reitillä"
LAYER_DEFAULT_ON = "Oletuksena päällä"
LAYER_OPACITY = "Läpinäkyvyys (0–1, tyhjä = tason oma)"
LAYER_ATTRIBUTION = "Nimeäminen (attribution)"
LAYER_URL = "Osoite"
LAYER_XYZ_URL = "Tiiliosoite ({z}/{x}/{y}-malli)"
LAYER_WMS_LAYERS = "WMS-taso (layers)"
LAYER_WMS_SERVICE_URL = "WMS-palvelun osoite"
LAYER_SERVICE_CATEGORIES = "Palvelukategoriat"
BUTTON_SAVE_LAYER = "Tallenna taso"
BUTTON_DELETE_LAYER = "Poista taso"
LAYER_SAVED = "Taso tallennettu: {path}"
LAYER_DELETED = "Taso poistettu: {layer_id}"
LAYER_NEW_WMS_HEADER = "Uusi WMS-taso"
LAYER_NEW_XYZ_HEADER = "Uusi XYZ-taso"
BUTTON_WMS_FETCH = "Hae tasot palvelimelta"
WMS_FETCHING = "Haetaan GetCapabilities…"
WMS_FETCHED = "Palvelin tarjoaa {count} tasoa"
WMS_FETCH_FAILED = "Haku epäonnistui: {error}"
WMS_FETCH_FIRST = "Hae tasot palvelimelta, niin nimet tulevat valittaviksi."
WMS_LAYER_OPTION = "{name} · {title}"
LAYER_NEEDS_ID_AND_NAME = "Anna tunniste ja nimi."
LAYER_XYZ_URL_HELP = "Ulkoinen avaimeton tiilipalvelu; selain kutsuu sitä suoraan."
LAYER_ID_TAKEN = "Tunniste {layer_id} on jo käytössä."
# mml_corridor layers (7.3): the tile cache state and the fetch button
LAYER_TILES_STATUS = "{needed} tiiltä tarvitaan · {cached} välimuistissa"
BUTTON_FETCH_TILES = "Hae puuttuvat tiilet"
TILES_KEY_MISSING = "Lisää MML_API_KEY .env-tiedostoon, niin tiilet voi hakea."
TILES_FETCHING = "Haetaan tiiliä Maanmittauslaitokselta…"
TILES_PROGRESS = "{done} / {total} tiiltä haettu"
TILES_FETCHED = "Haettu {downloaded} tiiltä, {failed} epäonnistui"

# Themes page
THEMES_INTRO = (
    "Järjestys määrää myös piirien järjestyksen tunnuksessa, sisältä ulos. "
    "Esitys-osio ratkaisee, mitkä tiedot nousevat reittilistaan ja reittikortin kärkeen."
)
THEME_HEADER = "{name} · järjestys {order}"
THEME_NAME = "Nimi"
THEME_TAGLINE = "Iskulause"
THEME_ORDER = "Järjestys"
THEME_COLOR_PRIMARY = "Pääväri"
THEME_COLOR_ROUTE = "Reittiviiva"
THEME_COLOR_HIGHLIGHT = "Korostus"
THEME_CONTRAST = "Kontrasti valkoista tekstiä vasten {ratio}:1"
THEME_CONTRAST_LOW = "Kontrasti alle 4,5:1 – valkoinen teksti ei ole luettavaa päävärin päällä."
THEME_DARK = "Tumma teema"
THEME_PRESENTATION_HEADER = "Esitys"
THEME_KEY_FIGURES = "Avainluvut"
THEME_BAND = "Nauha"
THEME_HERO_IMAGE = "Nosta kuva"
THEME_FILTERS = "Suodattimet"
THEME_SERVICES_FIRST = "Palvelut ensin (pilkuilla eroteltuna)"
THEME_BAND_TOO_MANY = "Nauhassa voi olla korkeuden lisäksi enintään {max} kaistaa."
KEY_FIGURE_NAMES = {
    "length": "pituus",
    "ascent": "nousu",
    "difficulty": "vaativuus",
    "itrs_technical": "ITRS tekninen",
    "itrs_endurance": "ITRS kestävyys",
    "itrs_exposure": "ITRS altistus",
    "itrs_wilderness": "ITRS erämaisuus",
    "dominant_surface": "pääpinta",
    "surface_shares": "pintaosuudet",
    "separated_share": "erotettu osuus",
    "winter_maintenance": "talvikunnossapito",
    "longest_service_gap": "pisin palveluväli",
}
BAND_LANE_NAMES = {
    "elevation": "korkeus",
    "surface": "pinta",
    "traffic": "liikenne",
    "itrs_technical": "ITRS tekninen",
}
HERO_IMAGE_NAMES = {"cover_image": "kansikuva", "hardest_section": "vaativin kohta"}
THEME_SAVED = "Teema tallennettu: {path}"

PROJECT_HEADER = "Projektiasetukset"
PROJECT_NAME = "Nimi"
PROJECT_SUBTITLE = "Alaotsikko"
PROJECT_AREA = "Alue (WGS84)"
PROJECT_AREA_FIELDS = ("lon min", "lat min", "lon max", "lat max")
PROJECT_DEFAULT_THEME = "Oletusteema"
PROJECT_DEFAULT_LANGUAGE = "Oletuskieli"
PROJECT_NEARBY_SERVICES_M = "Lähipalvelut (m)"
PROJECT_ITRS_HEADER = "ITRS-asteikot"
PROJECT_ITRS_EXPOSURE = "Altistus, tasoja"
PROJECT_ITRS_WILDERNESS = "Erämaisuus, tasoja"
PROJECT_ITRS_LOCKED = "lukittu"
PROJECT_ITRS_CAPTION = (
    "Tarkista tasojen määrä ITRS-oppaasta (itrs.bike) ja Suomen Ladun oppaasta. Kun asteikko on "
    "lukittu, validointi vaatii arvon 1…max ja frontend näyttää 'n / max'."
)
PROJECT_FEEDBACK_REPO = "Palaute: GitHub-repo"
PROJECT_FEEDBACK_FORM = "Palaute: issue-lomake"
PROJECT_SAVED = "Projektiasetukset tallennettu: {path}"
