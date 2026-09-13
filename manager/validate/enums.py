"""Check: enum values are allowed (7.2, Enum values).

The source models use Literal types for difficulty, seasons, surface, traffic, ITRS levels,
maintainer, reasons and section types, so a wrong value already stops the build when the
source data is read (build/read.py, with the field and the allowed values named). This check
therefore never finds anything; it exists so the UI lists every check of table 7.2.
"""

from typing import TYPE_CHECKING

from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData


def check_enums(source: "SourceData") -> list[Finding]:
    return []
