"""Check: theme presentation lists hold 5.7 identifiers only (7.2, Presentation identifiers).

The Presentation model (models/theme.py) uses Literal types for every list and limits `band`
to three lanes besides elevation, so a wrong identifier stops the build when the source data
is read. This check therefore never finds anything; it exists so the UI lists it.
"""

from typing import TYPE_CHECKING

from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData


def check_presentation(source: "SourceData") -> list[Finding]:
    return []
