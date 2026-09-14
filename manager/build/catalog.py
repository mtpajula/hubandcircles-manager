"""Build stage: catalog.json (5.6)."""

from datetime import UTC, datetime

from manager.build.read import SourceData
from manager.models import Catalog, CatalogProject, PublishedLayer, PublishedRoute, RouteSummary


def build_catalog(
    source: SourceData,
    routes: list[PublishedRoute],
    services: bool = False,
    layers: list[PublishedLayer] = (),
    coverage: dict[str, str] | None = None,
) -> Catalog:
    """`services`: whether services.geojson was written (5.6: absent until there are services);
    `coverage`: layer id -> coverage GeoJSON path of the corridor layers (7.3)."""
    p = source.project
    return Catalog(
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        project=CatalogProject(
            name=p.name,
            subtitle=p.subtitle,
            area=p.area,
            languages=p.languages,
            default_language=p.default_language,
            default_theme=p.default_theme,
            feedback=p.feedback,
        ),
        themes=sorted(source.themes, key=lambda t: t.order),
        layers=list(layers),
        routes=[RouteSummary.model_validate(r.model_dump()) for r in routes],
        overview="overview.geojson",
        services="services.geojson" if services else None,
        coverage=dict(coverage or {}),
    )
