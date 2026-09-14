"""Check: every layer card's source method is one the build can publish (5.4, ponytail)."""

from typing import TYPE_CHECKING

from manager.models import BUILT_METHODS
from manager.validate.finding import Finding

if TYPE_CHECKING:
    # Type-only: a runtime import would be circular (build imports validate).
    from manager.build.read import SourceData


def check_layers(source: "SourceData") -> list[Finding]:
    return [
        Finding(
            "warning",
            f"layer {layer.id}: source method {layer.source.method} not implemented yet",
        )
        for layer in source.layers
        if layer.source.method not in BUILT_METHODS
    ]
