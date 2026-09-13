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
    "links": "Linkit",
    "references": "Viittaukset",
    "translations": "Käännökset",
    "secrets": "Avainvuodot",
}
CHECK_PASSED = "✓ {name}"
CHECK_WARNING = "! {name} · {count} varoitusta"
CHECK_SHOW = "Näytä"

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

LIPAS_HEADER = "Lipas"
LIPAS_SNAPSHOT_AT = "Tilannekuva haettu {when}"
LIPAS_NO_SNAPSHOT = "Ei tilannekuvaa"
BUTTON_LIPAS_FETCH = "Hae Lipasista"
LIPAS_FETCHING = "Haetaan Lipasista…"
LIPAS_FETCHED = "Lipas haettu: {count} reittiä"
LIPAS_FETCH_FAILED = "Lipas-haku epäonnistui"
BUTTON_LIPAS_CREATE = "Luo puuttuvat reittikansiot"
LIPAS_MATCHING_LATER = "Jäljen vertailu Lipas-reitteihin tulee vaiheessa V2."

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
THEME_PRESENTATION_LATER = "Esitys-osio (avainluvut, nauha, suodattimet) tulee vaiheessa V2."
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
