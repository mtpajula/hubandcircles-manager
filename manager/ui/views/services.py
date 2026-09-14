"""Services page (ADMIN-UI-SPEC section 4), OSM and Visit Finland sources, stock Streamlit.

Thin: the fetch calls manager.sources.osm / visitfinland, the diff is snapshot.diff, and nothing
is written before the snapshot is accepted (7.6). The fetched list waits in st.session_state.
Manual markers (5.5) are edited below the OSM block and written by store.save_manual; no map
(V3b), so coordinates are typed or copied from an existing point.
"""

from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from manager import store
from manager.build import BuildError
from manager.build.read import read_source_data
from manager.build.services import merge
from manager.models import ManualMarker
from manager.models.identifiers import SERVICE_CATEGORIES
from manager.settings import data_dir, load_env
from manager.sources import osm, visitfinland
from manager.ui import texts
from manager.ui.widgets import lang_inputs, lang_text
from manager.validate.manual_markers import marker_warnings

load_env()
st.title(texts.PAGE_SERVICES)

source = data_dir()
if source is None:
    st.error(texts.DATA_DIR_MISSING)
    st.stop()
try:
    data = read_source_data(source)
except BuildError as e:
    st.error(texts.SOURCE_DATA_BROKEN.format(error=e))
    st.stop()

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))
if "flash_caption" in st.session_state:
    st.caption(st.session_state.pop("flash_caption"))


def name_of(service) -> str:
    return (service.name or {}).get("fi") or (service.name or {}).get("en") or ""


# --- Importer snapshots (7.6): OSM and Visit Finland behave the same ------------------------
def source_block(source_id: str, previous: list, module, fetch, labels: dict[str, str]) -> None:
    """Fetch → metrics and change table → accept. `fetch` returns the raw answer, None when the
    source is disabled (the caption says why); nothing is written before the accept button."""
    fetched_key = f"{source_id}_fetched"  # session key of the fetched, not yet accepted, list
    st.subheader(labels["header"])
    snapshot = module.snapshot_path(source)
    if snapshot.is_file():
        when = datetime.fromtimestamp(snapshot.stat().st_mtime, UTC).astimezone()
        st.caption(
            texts.SERVICES_SNAPSHOT_AT.format(
                when=when.strftime("%d.%m.%Y %H:%M"), count=len(previous)
            )
        )
    else:
        st.caption(texts.SERVICES_NO_SNAPSHOT)

    if st.button(labels["fetch"], key=f"{source_id}_fetch", disabled=fetch is None):
        with st.status(labels["fetching"]) as status:
            try:
                fetched = module.parse(fetch())
            except (ValueError, KeyError, OSError, visitfinland.SourceError) as e:
                status.update(label=labels["failed"], state="error")
                st.error(str(e))
            else:
                st.session_state[fetched_key] = fetched
                status.update(label=labels["fetched"].format(count=len(fetched)), state="complete")

    if fetched_key in st.session_state:
        fetched = st.session_state[fetched_key]
        changes = module.diff(previous, fetched)
        columns = st.columns(4)
        columns[0].metric(texts.METRIC_ADDED, f"+{len(changes.added)}")
        columns[1].metric(texts.METRIC_REMOVED, f"−{len(changes.removed)}")
        columns[2].metric(texts.METRIC_CHANGED, str(len(changes.changed)))
        columns[3].metric(texts.METRIC_TOTAL, str(len(fetched)))
        rows = [
            {
                texts.CHANGE_COLUMNS["change"]: texts.CHANGE_NAMES[kind],
                texts.CHANGE_COLUMNS["name"]: name_of(s),
                texts.CHANGE_COLUMNS["category"]: texts.SERVICE_CATEGORY_NAMES.get(
                    s.category, s.category
                ),
                texts.CHANGE_COLUMNS["id"]: s.id,
            }
            for kind, group in (
                ("added", changes.added),
                ("removed", changes.removed),
                ("changed", changes.changed),
            )
            for s in group
        ]
        st.markdown(f"**{texts.CHANGES_HEADER}**")
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        else:
            st.caption(texts.NO_CHANGES)
        # A correction whose target disappears with this snapshot (7.6).
        kept = [
            s for s in [*data.osm_services, *data.visitfinland_services] if s.source != source_id
        ]
        ids = {s.id for s in [*fetched, *kept]}
        for marker in data.manual_markers:
            if marker.replaces is not None and marker.replaces not in ids:
                st.warning(texts.MANUAL_TARGET_MISSING.format(target=marker.replaces))
        if st.button(texts.BUTTON_ACCEPT_SNAPSHOT, key=f"{source_id}_accept", type="primary"):
            path = module.write_snapshot(source, fetched)
            del st.session_state[fetched_key]
            st.session_state["flash"] = texts.SNAPSHOT_ACCEPTED.format(path=path)
            st.rerun()
    st.caption(texts.CLI_EQUIVALENT.format(command=f"python -m manager fetch {source_id}"))


source_block(
    "osm",
    data.osm_services,
    osm,
    lambda: osm.fetch(data.project.area),
    texts.OSM_LABELS,
)

city = data.project.municipality
try:
    vf_url, vf_key = visitfinland.api_settings()
except visitfinland.SourceError:
    vf_url = vf_key = None
if vf_key is None:
    st.caption(texts.SERVICES_VF_KEY_MISSING)
elif not city:
    st.caption(texts.SERVICES_VF_MUNICIPALITY_MISSING)
source_block(
    "visitfinland",
    data.visitfinland_services,
    visitfinland,
    (lambda: visitfinland.fetch(city, url=vf_url, key=vf_key)) if vf_key and city else None,
    texts.VF_LABELS,
)

# --- Manual markers (5.5) ----------------------------------------------------------------------
markers = data.manual_markers
snapshot_ids = {s.id for s in [*data.osm_services, *data.visitfinland_services]}


def save_markers(updated: list[ManualMarker]) -> None:
    path = store.save_manual(source, updated)
    st.session_state["flash"] = texts.MANUAL_SAVED.format(count=len(updated), path=path)
    st.session_state["flash_caption"] = texts.RUN_BUILD_REMINDER
    st.rerun()


def category_name(category: str) -> str:
    return texts.SERVICE_CATEGORY_NAMES.get(category, category)


st.subheader(texts.MANUAL_NEW_HEADER)
st.caption(texts.MANUAL_MARKERS_MAP_LATER)
lon_min, lat_min, lon_max, lat_max = data.project.area
with st.form("new_marker"):
    new_name = lang_inputs(texts.MANUAL_NAME, None, key="new_name")
    category = st.selectbox(
        texts.MANUAL_CATEGORY,
        SERVICE_CATEGORIES,
        format_func=category_name,
        key="new_category",
    )
    lon_column, lat_column = st.columns(2)
    lon = lon_column.number_input(
        texts.MANUAL_LON, value=(lon_min + lon_max) / 2, format="%.6f", step=1e-4, key="new_lon"
    )
    lat = lat_column.number_input(
        texts.MANUAL_LAT, value=(lat_min + lat_max) / 2, format="%.6f", step=1e-4, key="new_lat"
    )
    url = st.text_input(texts.MANUAL_URL, key="new_url")
    opening_hours = st.text_input(texts.MANUAL_OPENING_HOURS, key="new_opening_hours")
    new_description = lang_inputs(texts.MANUAL_DESCRIPTION, None, key="new_description")
    if st.form_submit_button(texts.BUTTON_SAVE_MARKER, type="primary"):
        name = lang_text(new_name)
        if not name:
            st.error(texts.MANUAL_NAME_REQUIRED)
        else:
            marker = ManualMarker(
                id=store.manual_id(name.get("fi") or name["en"], map(store.marker_key, markers)),
                name=name,
                category=category,
                source="manual",
                url=url.strip() or None,
                opening_hours=opening_hours.strip() or None,
                description=lang_text(new_description) or None,
                location=(lon, lat),
            )
            save_markers([*markers, marker])

st.subheader(texts.MANUAL_FIX_HEADER)
# The list as the build sees it: corrections applied, hidden points gone (delete the marker to
# bring one back); manual points are not targets, a correction targets a snapshot.
targets = {
    s.id: s
    for s in merge(data.osm_services, data.visitfinland_services, markers).services
    if s.source != "manual"
}
if not targets:
    st.caption(texts.MANUAL_FIX_NONE)
else:
    target = st.selectbox(
        texts.MANUAL_FIX_TARGET,
        list(targets),
        format_func=lambda i: " · ".join(
            filter(None, (i, name_of(targets[i]), category_name(targets[i].category)))
        ),
        key="fix_target",
    )
    existing = next((m for m in markers if m.replaces == target), None)
    k = f"_{target}"  # widget keys follow the selection so the defaults reload on change
    with st.form("fix_marker"):
        hidden = st.checkbox(
            texts.MANUAL_HIDE, value=bool(existing and existing.hidden), key=f"hide{k}"
        )
        st.caption(texts.MANUAL_KEEP_HINT)
        fix_name = lang_inputs(
            texts.MANUAL_NAME, existing.name if existing else None, key=f"fix_name{k}"
        )
        options = [texts.NONE_OPTION, *SERVICE_CATEGORIES]
        fix_category = st.selectbox(
            texts.MANUAL_CATEGORY,
            options,
            index=options.index(existing.category) if existing and existing.category else 0,
            format_func=category_name,
            key=f"fix_category{k}",
        )
        fix_url = st.text_input(
            texts.MANUAL_URL, value=(existing and existing.url) or "", key=f"fix_url{k}"
        )
        fix_hours = st.text_input(
            texts.MANUAL_OPENING_HOURS,
            value=(existing and existing.opening_hours) or "",
            key=f"fix_opening_hours{k}",
        )
        if st.form_submit_button(texts.BUTTON_SAVE_FIX, type="primary"):
            fields = {
                "name": lang_text(fix_name) or None,
                "category": None if fix_category == texts.NONE_OPTION else fix_category,
                "url": fix_url.strip() or None,
                "opening_hours": fix_hours.strip() or None,
            }
            fields = {key: value for key, value in fields.items() if value is not None}
            if hidden:
                marker = ManualMarker(replaces=target, hidden=True)
            elif fields:
                marker = ManualMarker(replaces=target, **fields)
            else:
                marker = None
                st.error(texts.MANUAL_FIX_NO_CHANGES)
            if marker is not None:
                save_markers([*(m for m in markers if m.replaces != target), marker])

st.subheader(texts.MANUAL_MARKERS_HEADER)
if markers:
    columns = texts.MANUAL_MARKER_COLUMNS
    st.dataframe(
        pd.DataFrame(
            [
                {
                    columns["id"]: m.id or "",
                    columns["replaces"]: m.replaces or "",
                    columns["hidden"]: m.hidden,
                    columns["name"]: (m.name or {}).get("fi") or (m.name or {}).get("en") or "",
                    columns["category"]: category_name(m.category) if m.category else "",
                }
                for m in markers
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    for warning in marker_warnings(markers, snapshot_ids):
        st.caption(warning)
    delete_column, button_column = st.columns([3, 1], vertical_alignment="bottom")
    doomed = delete_column.selectbox(
        texts.MANUAL_DELETE, [store.marker_key(m) for m in markers], key="delete_marker"
    )
    if button_column.button(texts.BUTTON_DELETE_MARKER, key="delete_marker_button"):
        save_markers([m for m in markers if store.marker_key(m) != doomed])
else:
    st.caption(texts.MANUAL_MARKERS_NONE)
