"""Result of a check."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class Finding:
    level: Literal["error", "warning", "info"]
    message: str
    check: str = ""  # key in manager.validate.CHECKS, set by check_all()
