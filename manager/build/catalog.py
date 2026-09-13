"""Build stage: catalog.json (5.6)."""

from datetime import UTC, datetime

from manager.build.read import SourceData
from manager.models import Catalog, CatalogProject, PublishedRoute, RouteSummary


def build_catalog(
    source: SourceData, routes: list[PublishedRoute], services: bool = False
) -> Catalog:
    """`services`: whether services.geojson was written (5.6: absent until there are services)."""
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
        layers=[],  # ponytail: V3 layer cards
        routes=[RouteSummary.model_validate(r.model_dump()) for r in routes],
        overview="overview.geojson",
        services="services.geojson" if services else None,
    )
