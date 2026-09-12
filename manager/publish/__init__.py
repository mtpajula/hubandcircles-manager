"""Publish: assemble the bundle, check limits per target, run the adapters (chapter 7.9)."""

from pathlib import Path

from pydantic import ValidationError

from manager.models import PublishSettings, Target
from manager.models.publish_settings import defaults
from manager.publish.bundle import Bundle, assemble
from manager.publish.errors import PublishError
from manager.publish.limits import check_limits
from manager.publish.targets import directory, github_pages

__all__ = ["Bundle", "PublishError", "publish", "read_settings"]

# ponytail: directory and github-pages only; cloudflare-pages, azure-swa and firebase in V4.
ADAPTERS = {"directory": directory.publish, "github-pages": github_pages.publish}


def read_settings(data_dir: Path) -> PublishSettings:
    """publish.json from source data, or defaults() if it is missing."""
    path = data_dir / "publish.json"
    if not path.is_file():
        return defaults()
    try:
        return PublishSettings.model_validate_json(path.read_bytes())
    except ValidationError as e:
        raise PublishError(f"{path}: {e}") from e


def _select(settings: PublishSettings, target_ids: list[str] | None) -> list[Target]:
    if target_ids is None:
        return settings.targets
    targets = {t.id: t for t in settings.targets}
    unknown = [i for i in target_ids if i not in targets]
    if unknown:
        raise PublishError(f"unknown target: {', '.join(unknown)}")
    return [targets[i] for i in target_ids]


def publish(
    data_dir: Path,
    dist_dir: Path,
    frontend: Path | None,
    work_dir: Path,
    target_ids: list[str] | None,
    dry_run: bool = False,
) -> Bundle:
    """Assemble the bundle into work_dir/bundle/ and publish it to the selected targets.

    target_ids=None means all configured targets, [] means assemble only. dry_run=True checks
    the limits but does not run the adapters. An error aborts before the first publish.
    bundle.published lists one line per target that was published.
    """
    settings = read_settings(data_dir)
    if frontend is None and settings.frontend.path:
        frontend = data_dir / settings.frontend.path
    if frontend is None:
        raise PublishError("frontend missing: pass --frontend or set frontend.path in publish.json")
    targets = _select(settings, target_ids)
    without_adapter = [t for t in targets if t.type not in ADAPTERS]
    if without_adapter and not dry_run:
        raise PublishError(
            "adapter not implemented yet: "
            + ", ".join(f"{t.id} ({t.type})" for t in without_adapter)
        )

    bundle = assemble(frontend, dist_dir, settings, work_dir / "bundle")
    errors = [x.message for t in targets for x in check_limits(bundle, t) if x.level == "error"]
    if errors:
        raise PublishError("\n".join(f"- {e}" for e in errors))
    if not dry_run:
        bundle.published = [ADAPTERS[t.type](bundle, t) for t in targets]
    return bundle
