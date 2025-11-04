class DjazzleError(Exception):
    """Base exception for Djazzle errors."""

    pass


class InvalidColumnError(DjazzleError):
    """Raised when a non-existent column is referenced."""

    pass
