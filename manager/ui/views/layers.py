"""Layers page (ADMIN-UI-SPEC section 3, simplified to the sources the build publishes).

Table of the cards, one expander per card for the frontend-side fields, and two forms for new
external layers: WMS (names fetched from GetCapabilities via manager.sources.wms) and XYZ.
Writes go through manager.store; the build derives `type` and checks the references.
"""

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from manager import store
from manager.build import BuildError
from manager.build.layers import layer_type
from manager.build.read import read_source_data
from manager.models import Layer, VisibleIn, Wms
from manager.models.identifiers import LAYER_SLOTS
from manager.settings import data_dir, load_env
from manager.sources import wms
from manager.ui import texts
from manager.ui.widgets import lang_inputs, lang_text

load_env()
st.title(texts.PAGE_LAYERS)

source = data_dir()
if source is None:
    st.error(texts.DATA_DIR_MISSING)
    st.stop()
try:
    data = read_source_data(source)
except BuildError as e:
    st.error(texts.SOURCE_DATA_BROKEN.format(error=e))
    st.stop()

st.caption(texts.LAYERS_INTRO)
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

theme_ids = [t.id for t in sorted(data.themes, key=lambda t: t.order)]
theme_names = {t.id: t.name.get("fi", t.id) for t in data.themes}
route_ids = [r.id for _, r in data.routes]
route_names = {r.id: r.name.get("fi", r.id) for _, r in data.routes}
layer_ids = [layer.id for layer in data.layers]


def name_of(layer: Layer) -> str:
    return layer.name.get("fi") or layer.name.get("en") or layer.id


def themes_text(layer: Layer) -> str:
    themes = layer.visible_in.themes
    return (
        texts.LAYER_ALL_THEMES
        if themes == "*"
        else ", ".join(theme_names.get(t, t) for t in themes)
    )


def save(layer: Layer) -> None:
    """Validate through the model, write, and rerun so the table shows the change."""
    try:
        path = store.save_layer(source, Layer.model_validate(layer.model_dump()))
    except (ValidationError, store.StoreError) as e:
        st.error(texts.SAVE_FAILED.format(error=e))
        return
    st.session_state["flash"] = texts.LAYER_SAVED.format(path=path)
    st.rerun()


def visibility_inputs(current: VisibleIn, key: str) -> VisibleIn:
    """The visibility block (section 3): every theme, or a list, plus routes."""
    st.markdown(f"**{texts.LAYER_VISIBILITY_HEADER}**")
    every = st.checkbox(
        texts.LAYER_ALL_THEMES_CHECKBOX, value=current.themes == "*", key=f"all_themes_{key}"
    )
    themes = st.multiselect(
        texts.LAYER_THEMES,
        theme_ids,
        default=[] if current.themes == "*" else [t for t in current.themes if t in theme_ids],
        format_func=theme_names.get,
        disabled=every,
        key=f"themes_{key}",
    )
    routes = st.multiselect(
        texts.LAYER_ROUTES,
        route_ids,
        default=[r for r in current.routes if r in route_ids],
        format_func=route_names.get,
        key=f"routes_{key}",
    )
    return VisibleIn(themes="*" if every else themes, routes=routes)


def common_inputs(layer: Layer | None, key: str) -> dict:
    """Name, slot, visibility, default, opacity and attribution; the fields every card has."""
    name = lang_inputs(texts.LAYER_NAME, layer.name if layer else None, f"layer_name_{key}")
    slot = st.selectbox(
        texts.LAYER_SLOT,
        LAYER_SLOTS,
        index=LAYER_SLOTS.index(layer.slot) if layer else 0,
        format_func=texts.LAYER_SLOT_NAMES.get,
        key=f"slot_{key}",
    )
    visible_in = visibility_inputs(layer.visible_in if layer else VisibleIn(), key)
    default_on = st.checkbox(
        texts.LAYER_DEFAULT_ON, value=layer.default_on if layer else False, key=f"default_on_{key}"
    )
    opacity = st.number_input(
        texts.LAYER_OPACITY,
        min_value=0.0,
        max_value=1.0,
        step=0.1,
        value=layer.opacity if layer else None,
        key=f"opacity_{key}",
    )
    attribution = st.text_input(
        texts.LAYER_ATTRIBUTION, value=layer.attribution if layer else "", key=f"attribution_{key}"
    )
    return {
        "name": lang_text(name),
        "slot": slot,
        "visible_in": visible_in,
        "default_on": default_on,
        "opacity": opacity,
        "attribution": attribution.strip(),
    }


# --- Table --------------------------------------------------------------------------------------
if data.layers:
    columns = texts.LAYER_COLUMNS
    st.dataframe(
        pd.DataFrame(
            [
                {
                    columns["id"]: layer.id,
                    columns["name"]: name_of(layer),
                    columns["slot"]: texts.LAYER_SLOT_NAMES.get(layer.slot, layer.slot),
                    columns["type"]: layer_type(layer) or texts.LAYER_TYPE_LATER,
                    columns["themes"]: themes_text(layer),
                    columns["default_on"]: texts.LAYER_ON if layer.default_on else texts.LAYER_OFF,
                }
                for layer in data.layers
            ]
        ),
        hide_index=True,
        width="stretch",
    )
else:
    st.caption(texts.LAYERS_NONE)

# --- One expander per card ----------------------------------------------------------------------
for layer in data.layers:
    k = layer.id
    with st.expander(texts.LAYER_EDIT_HEADER.format(name=name_of(layer))):
        st.caption(
            f"{texts.LAYER_SOURCE}: "
            f"{texts.LAYER_SOURCE_NAMES.get(layer.source.method, layer.source.method)}"
        )
        fields = common_inputs(layer, k)
        wms_layers = None
        if layer.wms is not None:
            wms_layers = st.text_input(
                texts.LAYER_WMS_LAYERS, value=layer.wms.layers, key=f"wms_layers_{k}"
            )
        save_column, confirm_column, delete_column = st.columns([1, 1, 1])
        if save_column.button(texts.BUTTON_SAVE_LAYER, key=f"save_layer_{k}", type="primary"):
            update = dict(fields)
            if wms_layers is not None:
                update["wms"] = layer.wms.model_copy(update={"layers": wms_layers.strip()})
            save(layer.model_copy(update=update))
        confirm = confirm_column.checkbox(texts.CONFIRM_DELETE, key=f"confirm_delete_{k}")
        if delete_column.button(texts.BUTTON_DELETE_LAYER, key=f"delete_layer_{k}"):
            if not confirm:
                st.warning(texts.DELETE_UNCONFIRMED)
            else:
                store.delete_layer(source, layer.id)
                st.session_state["flash"] = texts.LAYER_DELETED.format(layer_id=layer.id)
                st.rerun()


# --- New WMS layer ------------------------------------------------------------------------------
def new_layer(layer_id: str, fields: dict, **extra) -> Layer | None:
    """The card of a new-layer form, or None with an error shown."""
    if not layer_id.strip() or not fields["name"]:
        st.error(texts.LAYER_NEEDS_ID_AND_NAME)
        return None
    if layer_id.strip() in layer_ids:
        st.error(texts.LAYER_ID_TAKEN.format(layer_id=layer_id.strip()))
        return None
    try:
        return Layer(id=layer_id.strip(), **fields, **extra)
    except ValidationError as e:
        st.error(texts.SAVE_FAILED.format(error=e))
        return None


st.subheader(texts.LAYER_NEW_WMS_HEADER)
wms_url = st.text_input(
    texts.LAYER_WMS_SERVICE_URL,
    value="https://rovaniemi.asiointi.fi/teklaogcweb/WMS.ashx",
    key="wms_url",
)
if st.button(texts.BUTTON_WMS_FETCH, key="wms_fetch"):
    with st.status(texts.WMS_FETCHING) as status:
        try:
            offered = wms.capabilities(wms_url.strip())
        except (OSError, ValueError) as e:
            status.update(label=texts.WMS_FETCH_FAILED.format(error=e), state="error")
        else:
            st.session_state["wms_offered"] = offered
            status.update(label=texts.WMS_FETCHED.format(count=len(offered)), state="complete")
offered = st.session_state.get("wms_offered", [])
if offered:
    titles = {layer.name: layer.title for layer in offered}
    chosen = st.selectbox(
        texts.LAYER_WMS_LAYERS,
        list(titles),
        format_func=lambda n: (
            n if titles[n] == n else texts.WMS_LAYER_OPTION.format(name=n, title=titles[n])
        ),
        key="wms_chosen",
    )
else:
    st.caption(texts.WMS_FETCH_FIRST)
    chosen = st.text_input(texts.LAYER_WMS_LAYERS, key="wms_chosen_text")
wms_id = st.text_input(texts.LAYER_ID, help=texts.LAYER_ID_HELP, key="wms_id")
wms_fields = common_inputs(None, "new_wms")
if st.button(texts.BUTTON_SAVE_LAYER, key="save_new_wms", type="primary"):
    card = new_layer(
        wms_id,
        wms_fields,
        source={"method": "wms_external"},
        url=wms_url.strip(),
        wms=Wms(layers=chosen.strip()),
    )
    if card is not None:
        save(card)

# --- New XYZ layer ------------------------------------------------------------------------------
st.subheader(texts.LAYER_NEW_XYZ_HEADER)
xyz_url = st.text_input(texts.LAYER_XYZ_URL, help=texts.LAYER_XYZ_URL_HELP, key="xyz_url")
xyz_id = st.text_input(texts.LAYER_ID, help=texts.LAYER_ID_HELP, key="xyz_id")
xyz_fields = common_inputs(None, "new_xyz")
if st.button(texts.BUTTON_SAVE_LAYER, key="save_new_xyz", type="primary"):
    card = new_layer(xyz_id, xyz_fields, source={"method": "xyz_external"}, url=xyz_url.strip())
    if card is not None:
        save(card)
