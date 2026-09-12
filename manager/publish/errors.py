"""Exception that aborts publishing."""


class PublishError(Exception):
    """The bundle, limits or a target prevented publishing. The message states the reason."""
