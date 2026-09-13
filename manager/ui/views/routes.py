"""Routes page (ADMIN-UI-SPEC sections 2.1-2.3, 2.7), limited to the fields the Route model has.

Thin by rule 8: the form builds a Route and hands it to manager.store; metrics come from
manager.build.routes.process_route. A save or delete ends with st.rerun() so the selector and
the table reflect the new state; the message survives the rerun in st.session_state["flash"].
"""

from datetime import UTC, datetime

import streamlit as st
from pydantic import ValidationError

from manager import store
from manager.build import BuildError
from manager.build.read import read_source_data
from manager.build.routes import process_route
from manager.models import Route
from manager.settings import data_dir, load_env
from manager.sources import lipas
from manager.ui import texts

NEW = "__new__"  # selector value for "Uusi reitti"; not a slug, so it can never collide
LANGUAGES = ("fi", "en")
SEASONS = tuple(texts.SEASON_NAMES)
DIFFICULTIES = (None, *texts.DIFFICULTY_NAMES)
MAINTAINERS = (None, *texts.MAINTAINER_NAMES)

load_env()
st.title(texts.PAGE_ROUTES)

source = data_dir()
if source is None:
    st.error(texts.DATA_DIR_MISSING)
    st.stop()
try:
    data = read_source_data(source)
except BuildError as e:
    st.error(texts.SOURCE_DATA_BROKEN.format(error=e))
    st.stop()

theme_names = {t.id: t.name.get("fi", t.id) for t in sorted(data.themes, key=lambda t: t.order)}
routes = {route.id: route for _, route in data.routes}

flash = st.session_state.pop("flash", None)
if flash:
    st.success(flash)
if "select_next" in st.session_state:
    st.session_state["route_select"] = st.session_state.pop("select_next")


def cli(command: str) -> None:
    st.caption(texts.CLI_EQUIVALENT.format(command=command))


def lang_text(values: dict[str, str]) -> dict[str, str]:
    """Language object without empty strings (P11: missing text is left out, not written)."""
    return {lang: text.strip() for lang, text in values.items() if text.strip()}


# --- Form (left) and preview (right) ----------------------------------------------------------
form_column, preview_column = st.columns([460, 800])

with form_column:
    selected = st.selectbox(
        texts.ROUTE_SELECT,
        [NEW, *routes],
        format_func=lambda v: texts.ROUTE_NEW if v == NEW else routes[v].name.get("fi", v),
        key="route_select",
    )
    route = routes.get(selected)
    description = store.description(route) if route else {}
    missing = sum(
        1 for text in (route.name if route else {}, description) if not text.get("en", "").strip()
    )
    k = f"_{selected}"  # widget keys follow the selection so the defaults reload on change

    with st.form("route_form"):
        if route is None:
            route_id = st.text_input(texts.ROUTE_ID, key="route_id", help=texts.ROUTE_ID_HELP)
        else:
            st.text_input(texts.ROUTE_ID, value=route.id, disabled=True, key=f"route_id{k}")
            route_id = route.id
        names: dict[str, str] = {}
        descriptions: dict[str, str] = {}
        tab_labels = [texts.LANGUAGE_NAMES["fi"], texts.LANGUAGE_NAMES["en"]]
        if missing:
            tab_labels[1] += f" · {texts.MISSING_COUNT.format(count=missing)}"
        for lang, tab in zip(LANGUAGES, st.tabs(tab_labels)):
            with tab:
                names[lang] = st.text_input(
                    texts.ROUTE_NAME,
                    value=route.name.get(lang, "") if route else "",
                    key=f"name_{lang}{k}",
                )
                descriptions[lang] = st.text_area(
                    texts.ROUTE_DESCRIPTION, value=description.get(lang, ""), key=f"desc_{lang}{k}"
                )
        themes = st.multiselect(
            texts.ROUTE_THEMES,
            list(theme_names),
            default=[t for t in route.themes if t in theme_names] if route else [],
            format_func=theme_names.get,
            key=f"themes{k}",
        )
        seasons = st.multiselect(
            texts.ROUTE_SEASONS,
            SEASONS,
            default=[s for s in route.seasons if s in SEASONS] if route else [],
            format_func=texts.SEASON_NAMES.get,
            key=f"seasons{k}",
        )
        # Route.difficulty is a 5.7 value or None: legacy values are normalised on read.
        difficulty = st.selectbox(
            texts.ROUTE_DIFFICULTY,
            DIFFICULTIES,
            index=DIFFICULTIES.index(route.difficulty) if route else 0,
            format_func=lambda v: texts.DIFFICULTY_NAMES.get(v, v or texts.NONE_OPTION),
            key=f"difficulty{k}",
        )
        maintainer = st.selectbox(
            texts.ROUTE_MAINTAINER,
            MAINTAINERS,
            index=MAINTAINERS.index(route.maintainer) if route else 0,
            format_func=lambda v: texts.MAINTAINER_NAMES.get(v, texts.MAINTAINER_UNKNOWN),
            key=f"maintainer{k}",
        )
        # Inside a form the maintainer value updates on submit only, so the Lipas field follows
        # the last submitted value. ponytail: live disabling needs the selectbox outside the form.
        lipas_id = st.number_input(
            texts.ROUTE_LIPAS_ID,
            min_value=0,
            step=1,
            value=(route.lipas_id or 0) if route else 0,
            help=texts.ROUTE_LIPAS_ID_HELP,
            disabled=maintainer == "non_municipal",
            key=f"lipas_id{k}",
        )
        # ponytail: reasons and maintenance_note (2.7) when the Route model gets the fields (V2).
        gpx_file = st.file_uploader(
            texts.ROUTE_GPX,
            type=["gpx"],
            help=texts.ROUTE_GPX_KEEP if route else None,
            key=f"gpx{k}",
        )
        save_clicked = st.form_submit_button(texts.BUTTON_SAVE_ROUTE, type="primary")
        confirm_delete = st.checkbox(texts.CONFIRM_DELETE, key=f"confirm_delete{k}")
        delete_clicked = st.form_submit_button(texts.BUTTON_DELETE_ROUTE, disabled=route is None)

    if save_clicked:
        gpx = gpx_file.getvalue() if gpx_file else None
        if route is None and gpx is None:
            st.error(texts.ROUTE_CREATE_NEEDS_GPX)
        else:
            base = route or Route(id="", name={"fi": ""}, themes=[], seasons=[])
            try:
                card = store.with_description(
                    base.model_copy(
                        update={
                            "id": route_id.strip() if route is None else route_id,
                            "name": lang_text(names),
                            "themes": themes,
                            "seasons": seasons,
                            "difficulty": difficulty,
                            "maintainer": maintainer,
                            "lipas_id": int(lipas_id)
                            if lipas_id and maintainer != "non_municipal"
                            else None,
                        }
                    ),
                    lang_text(descriptions),
                )
                path = store.save_route(source, Route.model_validate(card.model_dump()), gpx)
            except (store.StoreError, ValidationError) as e:
                st.error(texts.SAVE_FAILED.format(error=e))
            else:
                st.session_state["flash"] = texts.ROUTE_SAVED.format(path=path)
                st.session_state["select_next"] = card.id
                st.rerun()
    if delete_clicked and route is not None:
        if not confirm_delete:
            st.warning(texts.DELETE_UNCONFIRMED)
        else:
            try:
                store.delete_route(source, route.id)
            except store.StoreError as e:
                st.error(str(e))
            else:
                st.session_state["flash"] = texts.ROUTE_DELETED.format(route_id=route.id)
                st.session_state["select_next"] = NEW
                st.rerun()

with preview_column:
    if route is None:
        st.info(texts.NO_ROUTE_SELECTED)
    else:
        try:
            result = process_route(store.route_dir(source, route.id), route)
        except BuildError as e:
            st.warning(texts.TRACK_BROKEN.format(error=e))
        else:
            length, ascent, images = st.columns(3)
            length.metric(texts.METRIC_LENGTH, f"{result.length_km:.1f} km".replace(".", ","))
            ascent.metric(
                texts.METRIC_ASCENT,
                texts.NONE_OPTION if result.ascent_m is None else f"{result.ascent_m} m",
            )
            images.metric(texts.METRIC_IMAGES, len(route.media))
            if result.ascent_m is None:
                st.caption(texts.NO_ELEVATIONS)
        # ponytail: map preview with streamlit-folium in V2b
        st.caption(texts.MAP_LATER)
    with st.sidebar:
        if route is not None:
            st.caption(
                texts.SIDEBAR_CURRENT_ROUTE.format(
                    name=route.name.get("fi", route.id),
                    themes=", ".join(theme_names.get(t, t) for t in route.themes),
                )
            )

# --- Table ----------------------------------------------------------------------------------
st.subheader(texts.ROUTES_TABLE_HEADER)
columns = texts.ROUTES_TABLE_COLUMNS
st.dataframe(
    [
        {
            columns["name"]: r.name.get("fi", r.id),
            columns["themes"]: ", ".join(theme_names.get(t, t) for t in r.themes),
            columns["translation"]: ", ".join(r.name),
            columns["maintainer"]: texts.MAINTAINER_SHORT.get(r.maintainer, texts.NONE_OPTION),
            columns["lipas_id"]: r.lipas_id,
        }
        for r in routes.values()
    ],
    width="stretch",
    hide_index=True,
)

# --- Lipas -----------------------------------------------------------------------------------
with st.expander(texts.LIPAS_HEADER):
    snapshot = lipas.snapshot_path(source)
    if snapshot.is_file():
        when = (
            datetime.fromtimestamp(snapshot.stat().st_mtime, UTC)
            .astimezone()
            .strftime("%d.%m.%Y %H:%M")
        )
        st.caption(texts.LIPAS_SNAPSHOT_AT.format(when=when))
    else:
        st.caption(texts.LIPAS_NO_SNAPSHOT)
    fetch_column, create_column = st.columns(2)
    if fetch_column.button(texts.BUTTON_LIPAS_FETCH, key="lipas_fetch"):
        with st.status(texts.LIPAS_FETCHING) as status:
            try:
                fetched = lipas.group(lipas.fetch(lipas.bbox_to_3067(data.project.area)))
            except (ValueError, OSError) as e:
                status.update(label=texts.LIPAS_FETCH_FAILED, state="error")
                st.error(str(e))
            else:
                lipas.write_snapshot(source, fetched)
                status.update(
                    label=texts.LIPAS_FETCHED.format(count=len(fetched)), state="complete"
                )
                st.text("\n".join(f"{r.lipas_id}  {r.type_code}  {r.name_fi}" for r in fetched))
    if create_column.button(
        texts.BUTTON_LIPAS_CREATE, key="lipas_create", disabled=not snapshot.is_file()
    ):
        st.text("\n".join(lipas.import_routes(source, lipas.read_snapshot(source))))
    cli("python -m manager import-lipas --create-routes")
    # ponytail: geometric matching of a track against the snapshot (2.7, 7.13) in V2.
    st.caption(texts.LIPAS_MATCHING_LATER)
