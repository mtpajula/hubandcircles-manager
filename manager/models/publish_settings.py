"""Publish settings (publish.json in source data), chapters 12.5 and 12.6."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

TargetType = Literal["directory", "cloudflare-pages", "github-pages", "azure-swa", "firebase"]
CachePolicy = Literal["immutable", "short", "none"]


class Frontend(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo: str | None = None
    version: str | None = None
    # ponytail: V0 uses only the path (local directory or zip); repo+version are fetched in V4.
    path: str | None = None


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: TargetType
    path: str | None = None
    project: str | None = None
    repo: str | None = None


class HeaderRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    cache: CachePolicy
    content_type: str | None = None


class PublishSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frontend: Frontend = Frontend()
    targets: list[Target] = []
    headers: list[HeaderRule]


def defaults() -> PublishSettings:
    """Header rules of chapter 12.5 without targets; used when publish.json is missing."""
    return PublishSettings(
        headers=[
            HeaderRule(path="/assets/*", cache="immutable"),
            HeaderRule(path="/data/**/*.webp", cache="immutable"),
            HeaderRule(
                path="/data/**/*.pmtiles", cache="immutable", content_type="application/vnd.pmtiles"
            ),
            HeaderRule(path="/data/layers/*/v*/*", cache="immutable"),
            HeaderRule(path="/data/**/*.gpx", cache="short", content_type="application/gpx+xml"),
            HeaderRule(path="/data/catalog.json", cache="short"),
            HeaderRule(path="/data/routes/*/route.json", cache="short"),
            HeaderRule(path="/index.html", cache="none"),
        ]
    )
