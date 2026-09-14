"""Change view of a service snapshot against the previous one (7.6), shared by the importers."""

from dataclasses import dataclass, field

from manager.models import Service


@dataclass
class Diff:
    added: list[Service] = field(default_factory=list)
    removed: list[Service] = field(default_factory=list)
    changed: list[Service] = field(default_factory=list)  # the new version
    unchanged: list[Service] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"added {len(self.added)}, removed {len(self.removed)}, changed {len(self.changed)},"
            f" unchanged {len(self.unchanged)}"
        )


def _content(service: Service) -> dict:
    return service.model_dump(exclude={"fetched_at"})


def diff(old: list[Service], new: list[Service]) -> Diff:
    """Change view against the previous snapshot by id (7.6); fetched_at does not count."""
    before = {s.id: s for s in old}
    result = Diff(removed=[s for s in old if s.id not in {n.id for n in new}])
    for service in new:
        previous = before.get(service.id)
        if previous is None:
            result.added.append(service)
        elif _content(previous) != _content(service):
            result.changed.append(service)
        else:
            result.unchanged.append(service)
    return result
