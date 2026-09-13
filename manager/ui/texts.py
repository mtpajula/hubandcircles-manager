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

COMING_S2 = "Tulee toimeksiannossa S2."
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

# Build & publish page
BUILD_HEADER = "Build"
BUTTON_BUILD = "Aja build"
BUILD_RUNNING = "Build käynnissä…"
BUILD_DONE = "Build valmis"
BUILD_FAILED = "Build keskeytyi, dist/ ennallaan"
BUILD_FINISHED_AT = "Valmistui {time} · {seconds} s"
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

PREVIEW_HEADER = "Esikatselu"
BUTTON_PREVIEW = "Esikatsele paikallisesti"
BUTTON_PREVIEW_STOP = "Pysäytä esikatselu"
PREVIEW_RUNNING = "Esikatselu käynnissä: {url}"
PREVIEW_STOPPED = "Esikatselu pysäytetty."
PREVIEW_FAILED = "Esikatselu keskeytyi."
FRONTEND_MISSING = (
    "Frontend-buildia ei löydy: {path}. Buildaa frontend: `cd hubandcircles-ui && npm run build`"
)

PUBLISH_HEADER = "Julkaisukohteet"
FRONTEND_CAPTION = "Frontend: {frontend}"
FRONTEND_PINNED = "{repo} v{version} (kiinnitetty publish.json-tiedostossa)"
NO_TARGETS = "Ei julkaisukohteita publish.json-tiedostossa."
BUTTON_PUBLISH = "Julkaise valittuihin kohteisiin"
PUBLISH_NO_SELECTION = "Valitse vähintään yksi kohde."
PUBLISH_RUNNING = "Julkaisu käynnissä…"
PUBLISH_DONE = "Julkaistu"
PUBLISH_FAILED = "Julkaisu keskeytyi"
PUBLISHED_TO = "Julkaistu:"

SOURCE_REPO_HEADER = "Lähdedata"
SOURCE_REPO_STATUS = (
    "{name} · haara {branch} · {changed} muutosta commitoimatta · {ahead} pushaamatta"
)
COMMIT_MESSAGE_LABEL = "Commit-viesti"
COMMIT_MESSAGE_DEFAULT = "Update route data"
BUTTON_COMMIT_PUSH = "Commitoi ja pushaa lähdedata"
COMMIT_RUNNING = "Commit ja push käynnissä…"
COMMIT_DONE = "Lähdedata pushattu"
COMMIT_FAILED = "Commit tai push epäonnistui"
COMMIT_NOTHING = "Ei commitoitavaa."
