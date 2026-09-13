"""Widget helpers shared by the views. Streamlit only; no logic, no writes (ADMIN-UI-SPEC 8)."""

import streamlit as st

from manager.ui import texts

LANGUAGES = ("fi", "en")


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
