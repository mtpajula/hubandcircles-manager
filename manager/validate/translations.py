"""Check: default-language text always exists, other languages missing is a warning (7.2, ch. 9)."""

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pydantic import BaseModel

from manager.validate.finding import Finding

if TYPE_CHECKING:
    # Type-only: a runtime import would be circular (build imports validate).
    from manager.build.read import SourceData


def is_lang_text(value: object, languages: set[str]) -> bool:
    """A non-empty dict whose keys are all declared languages and values strings (LangText)."""
    return (
        isinstance(value, dict)
        and bool(value)
        and all(k in languages for k in value)
        and all(isinstance(v, str) for v in value.values())
    )


def lang_texts(
    value: object, languages: set[str], path: str = ""
) -> Iterator[tuple[str, dict[str, str]]]:
    """Walk a model_dump() structure and yield (field path, lang text) pairs."""
    if is_lang_text(value, languages):
        yield path, value
    elif isinstance(value, dict):
        for key, inner in value.items():
            yield from lang_texts(inner, languages, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for i, inner in enumerate(value):
            yield from lang_texts(inner, languages, f"{path}[{i}]")


def _check(model: BaseModel, source: str, default_lang: str, langs: list[str]) -> list[Finding]:
    findings = []
    for path, text in lang_texts(model.model_dump(), set(langs)):
        for lang in langs:
            if lang not in text:
                level = "error" if lang == default_lang else "warning"
                findings.append(Finding(level, f"{source}: {path} missing language {lang}"))
    return findings


def check_translations(source: "SourceData") -> list[Finding]:
    default_lang, langs = source.project.default_language, source.project.languages
    if default_lang not in langs:
        langs = [default_lang, *langs]
    findings = _check(source.project, "project", default_lang, langs)
    for theme in source.themes:
        findings += _check(theme, f"theme {theme.id}", default_lang, langs)
    for _, route in source.routes:
        findings += _check(route, f"route {route.id}", default_lang, langs)
    return findings
