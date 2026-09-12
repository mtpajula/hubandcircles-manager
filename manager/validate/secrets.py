"""Check: no .env secret value appears in source or published data (chapter 13)."""

import os
from pathlib import Path

from manager.settings import ROOT
from manager.validate.finding import Finding

TEXT_SUFFIXES = {".json", ".geojson", ".gpx", ".md", ".yml"}
MIN_SECRET_LENGTH = 8


def env_variables(env_example: Path) -> list[str]:
    names = []
    for line in env_example.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            names.append(line.partition("=")[0].strip())
    return names


def check_secrets(
    directories: list[Path], env_example: Path = ROOT / ".env.example"
) -> list[Finding]:
    values = {
        name: os.environ[name]
        for name in env_variables(env_example)
        if len(os.environ.get(name, "")) >= MIN_SECRET_LENGTH
    }
    if not values:
        return []
    findings = []
    for directory in directories:
        for path in sorted(p for p in directory.rglob("*") if p.suffix in TEXT_SUFFIXES):
            content = path.read_text(encoding="utf-8", errors="ignore")
            for name, value in values.items():
                if value in content:
                    # The message names the variable and the file, never the value.
                    findings.append(Finding("error", f"{path}: contains the value of {name}"))
    return findings
