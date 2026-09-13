"""Themes page (ADMIN-UI-SPEC sections 6 and 6.1), limited to the fields the models have.

No st.form here: the contrast caption follows the colour picker live. Each save button builds
a model from the widgets and hands it to manager.store.
"""

import streamlit as st
from pydantic import ValidationError

from manager import store
from manager.build import BuildError
from manager.build.read import read_source_data
from manager.color import contrast_ratio
from manager.models import Colors, Feedback, ItrsScales, Project, Theme
from manager.settings import data_dir, load_env
from manager.ui import texts

WHITE = "#FFFFFF"
MIN_CONTRAST = 4.5
LANGUAGES = ("fi", "en")

load_env()
st.title(texts.PAGE_THEMES)

source = data_dir()
if source is None:
    st.error(texts.DATA_DIR_MISSING)
    st.stop()
try:
    data = read_source_data(source)
except BuildError as e:
    st.error(texts.SOURCE_DATA_BROKEN.format(error=e))
    st.stop()

st.caption(texts.THEMES_INTRO)


def lang_text(values: dict[str, str]) -> dict[str, str]:
    """Language object without empty strings (P11: missing text is left out, not written)."""
    return {lang: text.strip() for lang, text in values.items() if text.strip()}


def lang_inputs(label: str, current: dict[str, str] | None, key: str) -> dict[str, str]:
    """One text input per language in a row; returns {lang: raw value}."""
    columns = st.columns(len(LANGUAGES))
    return {
        lang: column.text_input(
            f"{label} ({texts.LANGUAGE_NAMES[lang]})",
            value=(current or {}).get(lang, ""),
            key=f"{key}_{lang}",
        )
        for lang, column in zip(LANGUAGES, columns)
    }


# --- Themes ----------------------------------------------------------------------------------
for theme in sorted(data.themes, key=lambda t: t.order):
    k = theme.id
    header = texts.THEME_HEADER.format(name=theme.name.get("fi", theme.id), order=theme.order)
    with st.expander(header):
        name = lang_inputs(texts.THEME_NAME, theme.name, f"theme_name_{k}")
        tagline = lang_inputs(texts.THEME_TAGLINE, theme.tagline, f"theme_tagline_{k}")
        order = st.number_input(
            texts.THEME_ORDER, min_value=1, step=1, value=theme.order, key=f"order_{k}"
        )
        primary_column, route_column, highlight_column = st.columns(3)
        primary = primary_column.color_picker(
            texts.THEME_COLOR_PRIMARY, theme.colors.primary, key=f"primary_{k}"
        )
        route = route_column.color_picker(
            texts.THEME_COLOR_ROUTE, theme.colors.route, key=f"route_{k}"
        )
        highlight = highlight_column.color_picker(
            texts.THEME_COLOR_HIGHLIGHT, theme.colors.highlight, key=f"highlight_{k}"
        )
        ratio = contrast_ratio(primary, WHITE)
        st.caption(texts.THEME_CONTRAST.format(ratio=f"{ratio:.1f}".replace(".", ",")))
        if ratio < MIN_CONTRAST:
            st.warning(texts.THEME_CONTRAST_LOW)
        dark = st.checkbox(texts.THEME_DARK, value=theme.dark, key=f"dark_{k}")
        # ponytail: presentation lists (6, ARKKITEHTUURI 5.7) when Theme gets `presentation` (V2).
        st.caption(texts.THEME_PRESENTATION_LATER)
        if st.button(texts.BUTTON_SAVE, key=f"save_theme_{k}"):
            try:
                updated = theme.model_copy(
                    update={
                        "name": lang_text(name),
                        "tagline": lang_text(tagline) or None,
                        "order": int(order),
                        "colors": Colors(primary=primary, route=route, highlight=highlight),
                        "dark": dark,
                    }
                )
                path = store.save_theme(source, Theme.model_validate(updated.model_dump()))
            except (store.StoreError, ValidationError) as e:
                st.error(texts.SAVE_FAILED.format(error=e))
            else:
                st.success(texts.THEME_SAVED.format(path=path))

# --- Project settings ------------------------------------------------------------------------
project = data.project
with st.expander(texts.PROJECT_HEADER):
    project_name = lang_inputs(texts.PROJECT_NAME, project.name, "project_name")
    subtitle = lang_inputs(texts.PROJECT_SUBTITLE, project.subtitle, "project_subtitle")
    st.caption(texts.PROJECT_AREA)
    area = tuple(
        column.number_input(label, value=float(value), format="%.4f", key=f"area_{i}")
        for i, (column, label, value) in enumerate(
            zip(st.columns(4), texts.PROJECT_AREA_FIELDS, project.area)
        )
    )
    theme_ids = [t.id for t in sorted(data.themes, key=lambda t: t.order)]
    default_theme = st.selectbox(
        texts.PROJECT_DEFAULT_THEME,
        theme_ids,
        index=theme_ids.index(project.default_theme) if project.default_theme in theme_ids else 0,
        key="default_theme",
    )
    default_language = st.selectbox(
        texts.PROJECT_DEFAULT_LANGUAGE,
        project.languages,
        index=project.languages.index(project.default_language),
        format_func=lambda v: texts.LANGUAGE_NAMES.get(v, v),
        key="default_language",
    )
    nearby_services_m = st.number_input(
        texts.PROJECT_NEARBY_SERVICES_M,
        min_value=0,
        step=50,
        value=project.nearby_services_m,
        key="nearby_services_m",
    )

    st.subheader(texts.PROJECT_ITRS_HEADER)
    scales: dict[str, int | None] = {}
    for dimension, label in (
        ("exposure", texts.PROJECT_ITRS_EXPOSURE),
        ("wilderness", texts.PROJECT_ITRS_WILDERNESS),
    ):
        current = getattr(project.itrs_scales, dimension)
        value_column, lock_column = st.columns([3, 1])
        levels = value_column.number_input(
            label, min_value=1, step=1, value=current or 1, key=f"itrs_{dimension}"
        )
        locked = lock_column.checkbox(
            texts.PROJECT_ITRS_LOCKED, value=current is not None, key=f"itrs_{dimension}_locked"
        )
        scales[dimension] = int(levels) if locked else None
    st.caption(texts.PROJECT_ITRS_CAPTION)

    feedback = project.feedback
    github_repo = st.text_input(
        texts.PROJECT_FEEDBACK_REPO,
        value=feedback.github_repo if feedback else "",
        key="github_repo",
    )
    issue_form = st.text_input(
        texts.PROJECT_FEEDBACK_FORM, value=feedback.issue_form if feedback else "", key="issue_form"
    )

    if st.button(texts.BUTTON_SAVE, key="save_project"):
        try:
            updated = project.model_copy(
                update={
                    "name": lang_text(project_name),
                    "subtitle": lang_text(subtitle),
                    "area": area,
                    "default_theme": default_theme,
                    "default_language": default_language,
                    "nearby_services_m": int(nearby_services_m),
                    "itrs_scales": ItrsScales(**scales),
                    "feedback": (
                        Feedback(github_repo=github_repo.strip(), issue_form=issue_form.strip())
                        if github_repo.strip() or issue_form.strip()
                        else None
                    ),
                }
            )
            path = store.save_project(source, Project.model_validate(updated.model_dump()))
        except (store.StoreError, ValidationError) as e:
            st.error(texts.SAVE_FAILED.format(error=e))
        else:
            st.success(texts.PROJECT_SAVED.format(path=path))
