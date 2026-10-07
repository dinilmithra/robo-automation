"""Shared generic automation type definitions."""

from __future__ import annotations

from typing import Any, Protocol, Union

from playwright.sync_api import Locator, Page

Scope = Union[Page, Locator]


class BrowserSession(Protocol):
    """Minimal browser contract used by consuming automation projects."""

    def new_context(self, **kwargs: Any) -> Any:
        """Create a browser context."""


__all__ = ["BrowserSession", "Scope"]
