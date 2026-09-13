"""Services page (ADMIN-UI-SPEC section 4), limited to the OSM source and stock Streamlit.

Thin: the fetch calls manager.sources.osm, the diff is osm.diff, and nothing is written before
the snapshot is accepted (7.6). The fetched list waits in st.session_state until then.
No map (V3b): manual markers are listed read-only.
"""

from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from manager.build import BuildError
from manager.build.read import read_source_data
from manager.settings import data_dir, load_env
from manager.sources import osm
from manager.ui import texts
from manager.validate.manual_markers import marker_warnings

FETCHED = "osm_fetched"  # session key of the fetched, not yet accepted, list

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


def name_of(service) -> str:
    return (service.name or {}).get("fi") or (service.name or {}).get("en") or ""


# --- OSM ---------------------------------------------------------------------------------------
st.subheader(texts.SERVICES_OSM_HEADER)
snapshot = osm.snapshot_path(source)
if snapshot.is_file():
    when = datetime.fromtimestamp(snapshot.stat().st_mtime, UTC).astimezone()
    st.caption(
        texts.SERVICES_SNAPSHOT_AT.format(
            when=when.strftime("%d.%m.%Y %H:%M"), count=len(data.osm_services)
        )
    )
else:
    st.caption(texts.SERVICES_NO_SNAPSHOT)

if st.button(texts.BUTTON_OSM_FETCH, key="osm_fetch"):
    with st.status(texts.OSM_FETCHING) as status:
        try:
            fetched = osm.parse(osm.fetch(data.project.area))
        except (ValueError, KeyError, OSError) as e:
            status.update(label=texts.OSM_FETCH_FAILED, state="error")
            st.error(str(e))
        else:
            st.session_state[FETCHED] = fetched
            status.update(label=texts.OSM_FETCHED.format(count=len(fetched)), state="complete")

if FETCHED in st.session_state:
    fetched = st.session_state[FETCHED]
    changes = osm.diff(data.osm_services, fetched)
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
    ids = {s.id for s in [*fetched, *data.visitfinland_services]}
    for marker in data.manual_markers:
        if marker.replaces is not None and marker.replaces not in ids:
            st.warning(texts.MANUAL_TARGET_MISSING.format(target=marker.replaces))
    if st.button(texts.BUTTON_ACCEPT_SNAPSHOT, key="osm_accept", type="primary"):
        path = osm.write_snapshot(source, fetched)
        del st.session_state[FETCHED]
        st.session_state["flash"] = texts.SNAPSHOT_ACCEPTED.format(path=path)
        st.rerun()
st.caption(texts.CLI_EQUIVALENT.format(command="python -m manager fetch osm"))
st.caption(texts.SERVICES_VF_LATER)

# --- Manual markers ----------------------------------------------------------------------------
st.subheader(texts.MANUAL_MARKERS_HEADER)
if data.manual_markers:
    columns = texts.MANUAL_MARKER_COLUMNS
    st.dataframe(
        pd.DataFrame(
            [
                {
                    columns["id"]: m.id or "",
                    columns["name"]: (m.name or {}).get("fi") or (m.name or {}).get("en") or "",
                    columns["category"]: texts.SERVICE_CATEGORY_NAMES.get(m.category or "", ""),
                    columns["replaces"]: m.replaces or "",
                    columns["hidden"]: m.hidden,
                }
                for m in data.manual_markers
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    ids = {s.id for s in [*data.osm_services, *data.visitfinland_services]}
    for warning in marker_warnings(data.manual_markers, ids):
        st.warning(warning)
else:
    st.caption(texts.MANUAL_MARKERS_NONE)
# ponytail: adding and editing markers on a map (ADMIN-UI-SPEC 4) in V3b.
st.caption(texts.MANUAL_MARKERS_MAP_LATER)
