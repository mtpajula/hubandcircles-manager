"""JSON Schema generation from the pydantic models (chapter 11)."""

import json
from pathlib import Path

from manager.models import Catalog, Project, PublishedRoute, PublishSettings, Route, Theme

MODELS = [Project, Theme, Route, Catalog, PublishedRoute, PublishSettings]


def generate(target: Path) -> list[Path]:
    """Write each model's schema to <target>/<model>.schema.json."""
    target.mkdir(parents=True, exist_ok=True)
    paths = []
    for model in MODELS:
        path = target / f"{model.__name__.lower()}.schema.json"
        content = json.dumps(
            model.model_json_schema(), sort_keys=True, indent=2, ensure_ascii=False
        )
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(path)
    return paths
