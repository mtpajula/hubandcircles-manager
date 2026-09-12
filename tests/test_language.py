"""P10 guard: every identifier, field name, enum value and comment in the package is English."""

import ast
import inspect
import json
import re
from pathlib import Path
from typing import get_args, get_origin

from pydantic import BaseModel

import manager.models

PACKAGE = Path(__file__).parent.parent / "manager"
SCHEMA = Path(__file__).parent.parent / "schema"

# Streamlit texts shown to the user are the only place Finnish prose is allowed (SKILL.md).
ALLOW_FINNISH_TEXT = {PACKAGE / "ui" / "texts.py"}

NON_ASCII_LETTERS = re.compile(r"[äöåÄÖÅ]")
FINNISH_STEMS = {
    "reitti", "reitit", "teema", "teemat", "taso", "tasot", "nimi", "kaudet", "vaativuus",
    "jalki", "palvelu", "palvelut", "tyokalu", "julkaise", "julkaisu", "esikatsele", "kaannos",
    "viittaus", "avain", "avaimet", "otsake", "otsakkeet", "raja", "rajat", "paketti", "kansio",
    "lahde", "virhe", "varoitus", "kuva", "kansikuva", "pituus", "nousu", "osio", "osiot",
    "tyyppi", "sisalto", "tekija", "lisenssi", "projekti", "kohde", "kohteet", "valimuisti",
    "polku", "versio", "kieli", "kielet", "oletus", "alue", "luokat", "selite", "attribuutio",
    "hae", "lue", "kirjoita", "tarkista", "kokoa", "mittaa", "vaihda", "generoi",
}  # fmt: skip


def _is_finnish(name: str) -> bool:
    if NON_ASCII_LETTERS.search(name):
        return True
    return any(token in FINNISH_STEMS for token in name.lower().split("_"))


def _python_files() -> list[Path]:
    return sorted(p for p in PACKAGE.rglob("*.py") if "__pycache__" not in p.parts)


def _names(tree: ast.Module) -> list[tuple[int, str]]:
    """(line, name) for definitions, arguments and module/class-level assignments."""
    found: list[tuple[int, str]] = []

    def targets(node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            found.append((node.lineno, node.id))
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                targets(elt)

    def assignments(body: list[ast.stmt]) -> None:
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    targets(t)
            elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
                targets(stmt.target)

    assignments(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.append((node.lineno, node.name))
            a = node.args
            for arg in [*a.posonlyargs, *a.args, *a.kwonlyargs, a.vararg, a.kwarg]:
                if arg is not None:
                    found.append((arg.lineno, arg.arg))
        elif isinstance(node, ast.ClassDef):
            found.append((node.lineno, node.name))
            assignments(node.body)
    return found


def test_python_identifiers_are_english():
    offenders = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders += [
            f"{path.relative_to(PACKAGE.parent)}:{line}: {name}"
            for line, name in _names(tree)
            if _is_finnish(name)
        ]
    assert not offenders, "Finnish identifiers (P10):\n" + "\n".join(offenders)


def test_python_text_has_no_finnish_letters():
    offenders = []
    for path in _python_files():
        if path in ALLOW_FINNISH_TEXT:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if NON_ASCII_LETTERS.search(line):
                offenders.append(f"{path.relative_to(PACKAGE.parent)}:{number}: {line.strip()}")
    assert not offenders, "Finnish letters in source (P10):\n" + "\n".join(offenders)


def _literal_values(annotation: object) -> list[str]:
    """Literal[...] string values anywhere inside a type annotation."""
    if get_origin(annotation) is None:
        return []
    args = get_args(annotation)
    values = [a for a in args if isinstance(a, str)]
    for a in args:
        values += _literal_values(a)
    return values


def test_model_fields_and_literals_are_english():
    offenders = []
    for name, cls in inspect.getmembers(manager.models, inspect.isclass):
        if not (issubclass(cls, BaseModel) and cls is not BaseModel):
            continue
        for field, info in cls.model_fields.items():
            if _is_finnish(field):
                offenders.append(f"{name}.{field}")
            offenders += [
                f"{name}.{field} = {v!r}"
                for v in _literal_values(info.annotation)
                if _is_finnish(v)
            ]
    assert not offenders, "Finnish model names (P10):\n" + "\n".join(offenders)


def _schema_strings(node: object, path: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                found += [(f"{path}.{k}", k) for k in value]
            if key == "enum" and isinstance(value, list):
                found += [(f"{path}.enum", v) for v in value if isinstance(v, str)]
            found += _schema_strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found += _schema_strings(value, f"{path}[{i}]")
    return found


def test_schema_properties_and_enums_are_english():
    offenders = []
    for path in sorted(SCHEMA.glob("*.schema.json")):
        for where, value in _schema_strings(json.loads(path.read_text()), path.name):
            if _is_finnish(value):
                offenders.append(f"{where}: {value}")
    assert not offenders, "Finnish schema names (P10):\n" + "\n".join(offenders)
