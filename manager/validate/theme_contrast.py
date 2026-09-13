"""Check: every theme primary colour has enough contrast for white text and for the snow
background (7.2, Theme colour contrast; UI-SPEC palette)."""

from typing import TYPE_CHECKING

from manager.color import contrast_ratio
from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData

MIN_CONTRAST = 4.5  # WCAG 2 AA for normal text
BACKGROUNDS = {"white": "#FFFFFF", "snow": "#F4F1EC"}


def check_theme_contrast(source: "SourceData") -> list[Finding]:
    findings = []
    for theme in source.themes:
        primary = theme.colors.primary
        for name, background in BACKGROUNDS.items():
            ratio = contrast_ratio(primary, background)
            if ratio < MIN_CONTRAST:
                findings.append(
                    Finding(
                        "error",
                        f"theme {theme.id}: colors.primary {primary} has contrast {ratio:.2f}:1"
                        f" against {name} {background}, at least {MIN_CONTRAST}:1 required",
                    )
                )
    return findings
