"""Routes page (ADMIN-UI-SPEC sections 2.1-2.7), limited to what stock Streamlit does.

Thin by rule 8: the main form and each expander below it build a Route and hand it to
manager.store; metrics and km come from manager.build. A save or delete ends with st.rerun() so
the selector and the table reflect the new state; the message survives the rerun in
st.session_state["flash"]. No map (streamlit-folium): a segment boundary is typed as km and the
hardest-section km is prefilled from the image EXIF.
"""

from datetime import UTC, datetime

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from manager import store
from manager.build import BuildError
from manager.build.media import read_exif
from manager.build.projection import km_along_lines
from manager.build.read import SourceData, read_source_data
from manager.build.routes import geometry_lines, process_route
from manager.build.segments import covered_km
from manager.models import HardestSection, Itrs, MediaInfo, Route, Segment
from manager.models.identifiers import (
    ITRS_LEVELS,
    MAINTAINERS,
    NON_MUNICIPAL_REASONS,
    SURFACES,
    TRAFFICS,
)
from manager.settings import data_dir, env, load_env
from manager.sources import lipas
from manager.ui import texts
from manager.ui.widgets import LANGUAGES, lang_inputs, lang_text
from manager.validate.maintenance_reasons import check_maintenance_reasons
from manager.validate.segments import TOLERANCE_KM, segment_problems

NEW = "__new__"  # selector value for "Uusi reitti"; not a slug, so it can never collide
SEASONS = tuple(texts.SEASON_NAMES)
DIFFICULTIES = (None, *texts.DIFFICULTY_NAMES)
MAINTAINER_OPTIONS = (None, *MAINTAINERS)
ITRS_OPTIONS = (None, *ITRS_LEVELS)
IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]
THUMBNAIL_WIDTH = 84
SEGMENT_ATTRIBUTES = ("surface", "traffic", "itrs_technical")

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


def decimal(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def option_label(names: dict[str, str]):
    return lambda v: names.get(v, texts.NONE_OPTION) if v else texts.NONE_OPTION


def save(updated: Route, message: str, images: list[tuple[str, bytes]] | None = None) -> None:
    """Write the full card (and new images) and rerun; the message survives as a flash."""
    try:
        store.save_route(source, Route.model_validate(updated.model_dump()), images=images)
    except (store.StoreError, ValidationError) as e:
        st.error(texts.SAVE_FAILED.format(error=e))
    else:
        st.session_state["flash"] = message
        st.session_state["select_next"] = updated.id
        st.rerun()


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
            format_func=option_label(texts.DIFFICULTY_NAMES),
            key=f"difficulty{k}",
        )
        if route is not None:
            itrs_level = route.itrs.technical if route.itrs else None
            hardest_km = route.hardest_section.km if route.hardest_section else None
            st.caption(
                texts.ITRS_SUMMARY.format(
                    itrs=texts.ITRS_LEVEL_NAMES.get(itrs_level, texts.ITRS_SUMMARY_NONE),
                    hardest=texts.HARDEST_SUMMARY_NONE
                    if hardest_km is None
                    else texts.HARDEST_SUMMARY_KM.format(km=decimal(hardest_km)),
                )
            )
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

result = None  # process_route output of the selected route; None without a readable track
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
            length.metric(texts.METRIC_LENGTH, f"{decimal(result.length_km)} km")
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

# --- Sections of the selected route (2.4-2.7 and images) --------------------------------------
if route is not None:
    directory = store.route_dir(source, route.id)

    # --- Images ---
    with st.expander(texts.IMAGES_HEADER):
        # The uploader key changes after a save so the saved files are not listed again.
        upload_round = st.session_state.get("upload_round", 0)
        uploads = st.file_uploader(
            texts.IMAGES_UPLOAD,
            type=IMAGE_TYPES,
            accept_multiple_files=True,
            help=texts.IMAGES_UPLOAD_HINT,
            key=f"images{k}_{upload_round}",
        )
        last_author = st.session_state.get("last_author", "")
        last_license = st.session_state.get("last_license", texts.IMAGE_LICENSE_DEFAULT)
        new_media: dict[str, MediaInfo] = {}
        files: list[tuple[str, bytes]] = []
        if uploads:
            st.markdown(f"**{texts.IMAGES_NEW_HEADER}**")
        for i, upload in enumerate(uploads or []):
            key = store.media_key(upload.name)
            image_column, author_column, license_column = st.columns([1, 3, 3])
            image_column.image(upload, width=THUMBNAIL_WIDTH)
            image_column.caption(key)
            author = author_column.text_input(
                texts.IMAGE_AUTHOR, value=last_author, key=f"new_author_{i}{k}"
            )
            licence = license_column.text_input(
                texts.IMAGE_LICENSE, value=last_license, key=f"new_license_{i}{k}"
            )
            new_media[key] = MediaInfo(author=author.strip(), license=licence.strip())
            files.append((upload.name, upload.getvalue()))

        if not route.media:
            st.caption(texts.IMAGES_NONE)
        removed: list[str] = []
        edited: dict[str, MediaInfo] = {}
        in_gallery_now = {
            key for s in route.sections if s.type == "gallery" for key in s.media
        } or set(route.media)  # a route without a gallery section shows every image
        in_gallery: list[str] = []
        for key, info in route.media.items():
            image_column, author_column, license_column, remove_column = st.columns([1, 3, 3, 1])
            if (directory / key).is_file():
                image_column.image(str(directory / key), width=THUMBNAIL_WIDTH)
            else:
                image_column.caption(texts.IMAGE_FILE_MISSING)
            image_column.caption(key)
            author = author_column.text_input(
                texts.IMAGE_AUTHOR, value=info.author, key=f"author_{key}{k}"
            )
            licence = license_column.text_input(
                texts.IMAGE_LICENSE, value=info.license, key=f"license_{key}{k}"
            )
            if remove_column.checkbox(texts.IMAGE_REMOVE, key=f"remove_{key}{k}"):
                removed.append(key)
            else:
                edited[key] = MediaInfo(author=author.strip(), license=licence.strip())
                if remove_column.checkbox(
                    texts.IMAGE_IN_GALLERY, value=key in in_gallery_now, key=f"gallery_{key}{k}"
                ):
                    in_gallery.append(key)
        cover_options = [None, *edited, *new_media]
        cover = st.selectbox(
            texts.COVER_IMAGE,
            cover_options,
            index=cover_options.index(route.cover_image) if route.cover_image in edited else 0,
            format_func=lambda v: v or texts.NONE_OPTION,
            key=f"cover{k}",
        )
        if st.button(texts.BUTTON_SAVE_IMAGES, key=f"save_images{k}"):
            media = edited | new_media
            incomplete = [key for key, info in media.items() if not (info.author and info.license)]
            if incomplete:
                st.error(texts.IMAGE_INFO_MISSING.format(key=", ".join(incomplete)))
            else:
                base = route
                try:
                    for key in removed:
                        base = store.remove_media(source, route.id, key)
                except store.StoreError as e:
                    st.error(texts.SAVE_FAILED.format(error=e))
                else:
                    if new_media:
                        latest = list(new_media.values())[-1]
                        st.session_state["last_author"] = latest.author
                        st.session_state["last_license"] = latest.license
                    st.session_state["upload_round"] = upload_round + 1
                    updated = base.model_copy(update={"media": media, "cover_image": cover})
                    save(
                        store.with_gallery(updated, [*in_gallery, *new_media]),
                        texts.IMAGES_SAVED.format(count=len(media)),
                        images=files,
                    )

    # --- ITRS assessment (2.4) ---
    with st.expander(texts.ITRS_HEADER):
        itrs = route.itrs or Itrs()
        scales = data.project.itrs_scales
        if scales.exposure is None or scales.wilderness is None:
            st.warning(texts.ITRS_SCALE_UNLOCKED)
        technical_column, endurance_column = st.columns(2)
        technical = technical_column.selectbox(
            texts.ITRS_TECHNICAL,
            ITRS_OPTIONS,
            index=ITRS_OPTIONS.index(itrs.technical),
            format_func=option_label(texts.ITRS_LEVEL_NAMES),
            key=f"itrs_technical{k}",
        )
        endurance = endurance_column.selectbox(
            texts.ITRS_ENDURANCE,
            ITRS_OPTIONS,
            index=ITRS_OPTIONS.index(itrs.endurance),
            format_func=option_label(texts.ITRS_LEVEL_NAMES),
            key=f"itrs_endurance{k}",
        )
        st.caption(texts.ITRS_LEVELS_CAPTION)
        exposure_column, wilderness_column = st.columns(2)
        exposure = exposure_column.number_input(
            texts.ITRS_EXPOSURE,
            min_value=0,
            max_value=scales.exposure,
            step=1,
            value=itrs.exposure or 0,
            help=texts.ITRS_ZERO_IS_NONE,
            key=f"itrs_exposure{k}",
        )
        wilderness = wilderness_column.number_input(
            texts.ITRS_WILDERNESS,
            min_value=0,
            max_value=scales.wilderness,
            step=1,
            value=itrs.wilderness or 0,
            help=texts.ITRS_ZERO_IS_NONE,
            key=f"itrs_wilderness{k}",
        )
        by_column, on_column = st.columns(2)
        assessed_by = by_column.text_input(
            texts.ITRS_ASSESSED_BY,
            value=itrs.assessed_by
            or env("ASSESSOR_NAME")
            or st.session_state.get("last_assessor", ""),
            key=f"itrs_assessed_by{k}",
        )
        assessed_on = on_column.date_input(
            texts.ITRS_ASSESSED_ON,
            value=itrs.assessed_on or datetime.now(UTC).astimezone().date(),
            key=f"itrs_on{k}",
        )
        if st.button(texts.BUTTON_SAVE_ITRS, key=f"save_itrs{k}"):
            st.session_state["last_assessor"] = assessed_by.strip()
            levels = (technical, endurance, int(exposure) or None, int(wilderness) or None)
            updated_itrs = (
                Itrs(
                    technical=technical,
                    endurance=endurance,
                    exposure=levels[2],
                    wilderness=levels[3],
                    assessed_by=assessed_by.strip() or None,
                    assessed_on=assessed_on,
                )
                if any(level is not None for level in levels)
                else None  # nothing assessed: no assessment (P11)
            )
            save(route.model_copy(update={"itrs": updated_itrs}), texts.ITRS_SAVED)

    # --- Hardest section (2.5) ---
    with st.expander(texts.HARDEST_HEADER):
        hardest = route.hardest_section
        media_options = [None, *route.media]
        if not route.media:
            st.caption(texts.HARDEST_NEEDS_IMAGES)
        hardest_media = st.selectbox(
            texts.HARDEST_MEDIA,
            media_options,
            index=media_options.index(hardest.media)
            if hardest and hardest.media in media_options
            else 0,
            format_func=lambda v: v or texts.NONE_OPTION,
            key=f"hardest_media{k}",
        )
        km_value = hardest.km if hardest and hardest.media == hardest_media else None
        km_caption = None
        if hardest_media is not None:
            if (directory / hardest_media).is_file():
                st.image(str(directory / hardest_media), width=THUMBNAIL_WIDTH)
            if km_value is None and result is not None:
                location = read_exif(directory / hardest_media).location
                if location is None:
                    km_caption = texts.HARDEST_KM_NO_EXIF
                else:
                    lines = geometry_lines(result.track["geometry"])
                    km_value = round(km_along_lines(lines, location), 1)
                    km_caption = texts.HARDEST_KM_FROM_EXIF
        # The key follows the image so that a new choice gets its own EXIF prefill.
        km = st.number_input(
            texts.HARDEST_KM,
            min_value=0.0,
            max_value=result.length_km + TOLERANCE_KM if result else None,
            step=0.1,
            format="%.1f",
            value=km_value,
            key=f"hardest_km_{hardest_media}{k}",
        )
        if km_caption:
            st.caption(km_caption)
        hardest_description = lang_inputs(
            texts.HARDEST_DESCRIPTION, hardest.description if hardest else None, f"hardest_desc{k}"
        )
        if st.button(texts.BUTTON_SAVE_HARDEST, key=f"save_hardest{k}"):
            updated_hardest = (
                HardestSection(
                    media=hardest_media,
                    km=km,
                    description=lang_text(hardest_description) or None,
                )
                if hardest_media
                else None
            )
            save(route.model_copy(update={"hardest_section": updated_hardest}), texts.HARDEST_SAVED)

    # --- Segment editor (2.6) ---
    with st.expander(texts.SEGMENTS_HEADER):
        length_km = result.length_km if result else 0.0
        covered = min(covered_km(route.segments), length_km)
        st.markdown(
            "**"
            + texts.SEGMENTS_COVERAGE.format(
                percent=round(100 * covered / length_km) if length_km else 0,
                unknown_km=decimal(length_km - covered),
            )
            + "**"
        )
        # ponytail: no elevation profile with boundary lines; the table is the editor.
        frame = pd.DataFrame(
            [s.model_dump() for s in route.segments], columns=list(texts.SEGMENT_COLUMNS)
        ).astype({"start_km": float, "end_km": float})
        km_column = {
            "min_value": 0.0,
            "max_value": length_km + TOLERANCE_KM,
            "step": 0.01,
            "format": "%.2f",
            "required": True,
        }
        choice = {
            "surface": (SURFACES, texts.SURFACE_NAMES),
            "traffic": (TRAFFICS, texts.TRAFFIC_NAMES),
            "itrs_technical": (ITRS_LEVELS, texts.ITRS_LEVEL_NAMES),
        }
        edited_frame = st.data_editor(
            frame,
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            column_config={
                "start_km": st.column_config.NumberColumn(
                    texts.SEGMENT_COLUMNS["start_km"], **km_column
                ),
                "end_km": st.column_config.NumberColumn(
                    texts.SEGMENT_COLUMNS["end_km"], **km_column
                ),
                **{
                    attribute: st.column_config.SelectboxColumn(
                        texts.SEGMENT_COLUMNS[attribute],
                        options=list(options),
                        format_func=names.get,
                        required=False,
                    )
                    for attribute, (options, names) in choice.items()
                },
            },
            key=f"segments_editor{k}",
        )
        segments: list[Segment] = []
        problems: list[str] = []
        for row_number, row in enumerate(edited_frame.to_dict("records"), start=1):
            if pd.isna(row["start_km"]) or pd.isna(row["end_km"]):
                problems.append(texts.SEGMENTS_INCOMPLETE_ROW.format(row=row_number))
                continue
            segments.append(
                Segment(
                    start_km=float(row["start_km"]),
                    end_km=float(row["end_km"]),
                    **{a: None if pd.isna(row[a]) else row[a] for a in SEGMENT_ATTRIBUTES},
                )
            )
        problems += [
            texts.SEGMENTS_PROBLEM.format(problem=p) for p in segment_problems(segments, length_km)
        ]
        for problem in problems:
            st.error(problem)
        st.caption(texts.SEGMENTS_MAP_CLICK_LATER)
        if st.button(
            texts.BUTTON_SAVE_SEGMENTS,
            type="primary",
            disabled=bool(problems) or result is None,
            key=f"save_segments{k}",
        ):
            save(
                route.model_copy(update={"segments": segments}),
                texts.SEGMENTS_SAVED.format(count=len(segments)),
            )

    # --- Maintenance (2.7) ---
    with st.expander(texts.MAINTENANCE_HEADER):
        maintainer = st.selectbox(
            texts.ROUTE_MAINTAINER,
            MAINTAINER_OPTIONS,
            index=MAINTAINER_OPTIONS.index(route.maintainer),
            format_func=lambda v: texts.MAINTAINER_NAMES.get(v, texts.MAINTAINER_UNKNOWN),
            key=f"maintainer{k}",
        )
        reasons: list[str] = []
        note: dict[str, str] = {}
        lipas_id = 0
        if maintainer == "non_municipal":
            st.text_input(
                texts.ROUTE_LIPAS_ID, value=texts.LIPAS_NO_LINK, disabled=True, key=f"lipas_none{k}"
            )
            st.markdown(f"**{texts.REASONS_HEADER}**")
            reasons = [
                reason
                for reason in NON_MUNICIPAL_REASONS
                if st.checkbox(
                    texts.REASON_NAMES[reason],
                    value=reason in route.non_municipal_reasons,
                    key=f"reason_{reason}{k}",
                )
            ]
            note = lang_inputs(texts.MAINTENANCE_NOTE, route.maintenance_note, f"note{k}")
        else:
            lipas_id = st.number_input(
                texts.ROUTE_LIPAS_ID,
                min_value=0,
                step=1,
                value=route.lipas_id or 0,
                help=texts.ROUTE_LIPAS_ID_HELP,
                key=f"lipas_id{k}",
            )
        # ponytail: Lipas suggestion from the track (2.7, 7.13) needs geometric matching (V6).
        st.caption(texts.LIPAS_SUGGESTION_LATER)
        if st.button(texts.BUTTON_SAVE_MAINTENANCE, key=f"save_maintenance{k}"):
            updated = route.model_copy(
                update={
                    "maintainer": maintainer,
                    "lipas_id": int(lipas_id) or None,
                    "non_municipal_reasons": reasons,
                    "maintenance_note": lang_text(note) or None,
                }
            )
            # The build's own check decides (rule 8); its message is shown under the spec text.
            errors = [
                f
                for f in check_maintenance_reasons(
                    SourceData(data.project, data.themes, [(directory, updated)])
                )
                if f.level == "error"
            ]
            if errors:
                st.error(texts.MAINTENANCE_NO_REASON)
                for finding in errors:
                    st.caption(finding.message)
            else:
                save(updated, texts.MAINTENANCE_SAVED)

# --- Table ----------------------------------------------------------------------------------
st.subheader(texts.ROUTES_TABLE_HEADER)
columns = texts.ROUTES_TABLE_COLUMNS


def maintainer_cell(r: Route) -> str:
    cell = texts.MAINTAINER_SHORT.get(r.maintainer, texts.NONE_OPTION)
    if r.maintainer == "non_municipal":
        cell += f" · {texts.REASON_COUNT.format(count=len(r.non_municipal_reasons))}"
    return cell


st.dataframe(
    [
        {
            columns["name"]: r.name.get("fi", r.id),
            columns["themes"]: ", ".join(theme_names.get(t, t) for t in r.themes),
            columns["translation"]: ", ".join(r.name),
            columns["maintainer"]: maintainer_cell(r),
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
    # ponytail: geometric matching of a track against the snapshot (2.7, 7.13) in V6.
    st.caption(texts.LIPAS_MATCHING_LATER)
