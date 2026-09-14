# hubandcircles-manager

Management tool for **Napa ja piirit / Hub & Circles** (cycling routes around Rovaniemi).
Python package `manager` with a thin Streamlit UI. It imports, builds, validates and publishes
the source data of [hubandcircles-data](https://github.com/mtpajula/hubandcircles-data) together
with the [hubandcircles-ui](https://github.com/mtpajula/hubandcircles-ui) frontend as a static
site. Architecture: `../ARKKITEHTUURI.md` (Finnish prose, English identifiers). Admin UI spec:
`ADMIN-UI-SPEC.md`.

## Setup

```bash
uv sync
cp .env.example .env      # fill in DATA_DIR (e.g. ../hubandcircles-data) and the keys you have
```

`.env` is gitignored. Variables: `DATA_DIR`, `SOURCE_FILES_DIR`, `TILE_CACHE_DIR`, `PMTILES_BIN`,
`MML_API_KEY`, `VF_API_KEY`, `VF_API_SECONDARY_KEY`, `GITHUB_TOKEN` (optional; without it git's own
credential helper is used for publishing).

## Use

```bash
uv run streamlit run manager/ui/app.py          # admin UI (Finnish)
uv run python -m manager build                  # source data → dist/
uv run python -m manager preview --frontend ../hubandcircles-ui/dist   # http://127.0.0.1:8765
uv run python -m manager publish --frontend ../hubandcircles-ui/dist   # to publish.json targets
uv run python -m manager import-lipas [--create-routes]                # Lipas register snapshot
uv run python -m manager fetch tiles [--layer ID]   # MML corridor tiles into TILE_CACHE_DIR (.tiles/)
uv run python -m manager schema                 # regenerate schema/ from the pydantic models
```

Every UI button names its CLI equivalent. Logic lives in the package; `manager/ui/` only calls it.

## Development

Done command: `uv run ruff check && uv run ruff format --check && uv run pytest -q`.
Rules: `.claude/skills/manager-dev/SKILL.md`. Identifiers are English (P10); the only Finnish
strings are the UI texts in `manager/ui/texts.py`.
