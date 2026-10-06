"""Playwright BrowserContext wrapper for browser automation browser lifecycle control."""

from __future__ import annotations

from typing import Any, Callable

from playwright.sync_api import BrowserContext

from robo_automation.framework.robo_page import RoboPage


class RoboBrowserContext:
    """Own a Playwright browser context behind the browser automation boundary."""

    def __init__(self, context: BrowserContext) -> None:
        if not isinstance(context, BrowserContext):
            raise TypeError("RoboBrowserContext requires a Playwright BrowserContext.")
        self._context = context

    @classmethod
    def get(cls, context: BrowserContext) -> "RoboBrowserContext":
        """Wrap a Playwright ``BrowserContext`` in a new ``RoboBrowserContext``."""
        return cls(context)

    def new_page(self) -> RoboPage:
        """Create a new Playwright page and wrap it as a generic ``RoboPage``."""
        return RoboPage.get(self._context.new_page())

    @property
    def pages(self) -> list[RoboPage]:
        """Return the context's current pages as ``RoboPage`` objects."""
        return [RoboPage.get(page) for page in self._context.pages]

    def storage_state(self, **kwargs: Any) -> dict[str, Any]:
        """Return storage state for this context."""
        return self._context.storage_state(**kwargs)

    def set_default_timeout(self, timeout: float) -> None:
        """Set the default operation timeout in milliseconds."""
        self._context.set_default_timeout(timeout)

    def set_default_navigation_timeout(self, timeout: float) -> None:
        """Set the default navigation timeout in milliseconds."""
        self._context.set_default_navigation_timeout(timeout)

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        """Register an event callback without exposing the BrowserContext."""
        if event == "page":
            self._context.on(event, lambda page: callback(RoboPage.get(page)))
            return
        self._context.on(event, callback)

    def close(self, **kwargs: Any) -> None:
        """Close the owned browser context."""
        self._context.close(**kwargs)
