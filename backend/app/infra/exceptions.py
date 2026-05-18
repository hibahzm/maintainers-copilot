class DomainError(Exception):
    """Base class for expected application failures."""


class NotFoundError(DomainError):
    """Raised when an entity does not exist."""


class PermissionDenied(DomainError):
    """Raised when the caller cannot perform an action."""


class ToolFailure(DomainError):
    """Raised when an external dependency fails in a controlled way."""
