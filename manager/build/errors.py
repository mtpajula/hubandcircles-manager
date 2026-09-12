"""Exception that aborts the build."""


class BuildError(Exception):
    """Source data or a check prevented the build. The message names the file and the reason."""
