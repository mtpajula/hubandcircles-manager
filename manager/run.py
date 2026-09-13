"""Subprocess helpers that never fork().

pyproj (PROJ) registers an atfork handler that closes its SQLite handles in the child; on macOS
that segfaults, so after the first coordinate transform every forked child dies (exit -11).
CPython uses posix_spawn instead of fork when close_fds=False, cwd is None and the executable is
an absolute path – the three rules these helpers enforce. Use `git -C <dir>` instead of cwd.
"""

import shutil
import subprocess
from typing import Any


def _resolve(args: list[str]) -> list[str]:
    executable = shutil.which(args[0])
    if executable is None:
        raise FileNotFoundError(args[0])
    return [executable, *args[1:]]


def run(args: list[str], *, check: bool = False, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """subprocess.run with text output captured, posix_spawn-compatible."""
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    assert "cwd" not in kwargs, "use `git -C` or an absolute path instead of cwd (fork is unsafe)"
    return subprocess.run(_resolve(args), check=check, close_fds=False, **kwargs)


def popen(args: list[str], **kwargs: Any) -> subprocess.Popen:
    """subprocess.Popen, posix_spawn-compatible."""
    assert "cwd" not in kwargs, (
        "set PYTHONPATH or use absolute paths instead of cwd (fork is unsafe)"
    )
    return subprocess.Popen(_resolve(args), close_fds=False, **kwargs)
