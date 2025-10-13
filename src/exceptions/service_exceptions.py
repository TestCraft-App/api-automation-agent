from .base import AppError


class FrameworkTemplateCopyError(AppError):
    """Raised when copying the framework template fails."""

    def __init__(self, destination: str, original_exception: Exception):
        self.destination = destination
        self.original_exception = original_exception
        super().__init__(f"Failed to copy framework template to '{destination}': {original_exception}")
