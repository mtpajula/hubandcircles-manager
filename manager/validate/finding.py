"""Result of a check."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class Finding:
    level: Literal["error", "warning"]
    message: str
    check: str = ""  # key in manager.validate.CHECKS, set by check_all()
