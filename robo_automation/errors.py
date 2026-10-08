"""Public exception types for robo-automation consumers."""

from __future__ import annotations

from typing import Any, Mapping


class RoboAutomationError(RuntimeError):
    """Base exception for failures reported by :mod:`robo_automation`.

    Consumer projects can catch this exception instead of depending on the
    underlying browser engine's exception types.

    Args:
        message: Clear description of what failed.
        code: Optional stable machine-readable error code.
        details: Optional structured context that helps diagnose the failure.

    Attributes:
        code: Stable error code suitable for logs or conditional handling.
        details: Read-only copy of the supplied diagnostic context.
    """

    default_code = "ROBO_AUTOMATION_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        normalized_message = " ".join(str(message or "").split())
        if not normalized_message:
            normalized_message = "robo-automation operation failed."
        super().__init__(normalized_message)
        self.code = str(code or self.default_code)
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        """Return a structured representation suitable for logs or reports."""
        return {
            "type": type(self).__name__,
            "code": self.code,
            "message": str(self),
            "details": dict(self.details),
        }
