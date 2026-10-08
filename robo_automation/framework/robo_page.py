"""Playwright Page wrapper used by consuming browser automation projects."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Pattern

from playwright.sync_api import Locator, Page

from robo_automation.framework.robo_locator import RoboLocator


class RoboPage:
    """Own a Playwright ``Page`` behind the browser automation framework boundary."""

    locator_class: type[RoboLocator] = RoboLocator

    def __init__(self, page: Page) -> None:
        if not isinstance(page, Page):
            raise TypeError("RoboPage requires a Playwright Page.")
        self._page = page

    @classmethod
    def get(cls, page: Page) -> "RoboPage":
        """Wrap a Playwright ``Page`` in a new ``RoboPage``."""
        return cls(page)

    def specialize(self, page_type: type["RoboPage"]) -> "RoboPage":
        """Return ``page_type`` around the same owned Playwright page.

        This is the controlled extension point used by higher-level automation
        libraries (for example ``robo-appian``) to specialize a generic page
        without taking ownership of the underlying Playwright page lifecycle.
        """
        if not issubclass(page_type, RoboPage):
            raise TypeError("page_type must derive from RoboPage.")
        if isinstance(self, page_type):
            return self
        return page_type.get(self._page)

    @property
    def url(self) -> str:
        """Return the current page URL."""
        return self._page.url

    @property
    def main_frame(self):
        """Return the current main frame for event/diagnostic comparison."""
        return self._page.main_frame

    def goto(self, url: str, **kwargs: Any):
        """Navigate to ``url``."""
        return self._page.goto(url, **kwargs)

    def reload(self, **kwargs: Any):
        """Reload the current page."""
        return self._page.reload(**kwargs)

    def title(self) -> str:
        """Return the document title."""
        return self._page.title()

    def close(self, **kwargs: Any) -> None:
        """Close the page."""
        self._page.close(**kwargs)

    def is_closed(self) -> bool:
        """Return whether the page is closed."""
        return self._page.is_closed()

    def bring_to_front(self) -> None:
        """Bring this page to the front."""
        self._page.bring_to_front()

    def content(self) -> str:
        """Return the current page HTML."""
        return self._page.content()

    def screenshot(self, **kwargs: Any):
        """Capture a screenshot."""
        return self._page.screenshot(**kwargs)

    def evaluate(self, expression: str, arg: Any = None):
        """Evaluate JavaScript in the page."""
        if arg is None:
            return self._page.evaluate(expression)
        return self._page.evaluate(expression, arg)

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        """Register a page event callback."""
        self._page.on(event, callback)

    def wait_for_load_state(self, state: str | None = None, **kwargs: Any) -> None:
        """Wait for the requested load state."""
        self._page.wait_for_load_state(state, **kwargs)

    def expect_popup(self, **kwargs: Any):
        """Return Playwright's popup expectation context for internal components."""
        return self._page.expect_popup(**kwargs)

    def locator(self, selector: str, **kwargs: Any) -> Locator:
        """Create a Playwright locator through the controlled page interface."""
        return self._page.locator(selector, **kwargs)

    def get_by_role(self, role: str, **kwargs: Any) -> Locator:
        """Create a role-based locator through the controlled page interface."""
        return self._page.get_by_role(role, **kwargs)

    def get_by_text(self, text: str | Pattern[str], **kwargs: Any) -> Locator:
        """Create a text locator through the controlled page interface."""
        return self._page.get_by_text(text, **kwargs)

    def get_by_title(self, text: str | Pattern[str], **kwargs: Any) -> Locator:
        """Create a title locator through the controlled page interface."""
        return self._page.get_by_title(text, **kwargs)

    def press(self, selector: str, key: str, **kwargs: Any) -> None:
        """Press ``key`` on an element matching ``selector``."""
        self._page.press(selector, key, **kwargs)

    def press_key(self, key: str) -> None:
        """Press a keyboard key at page scope."""
        self._page.keyboard.press(key)

    def same_page(self, other: "RoboPage") -> bool:
        """Return whether both wrappers own the exact same Playwright page."""
        return isinstance(other, RoboPage) and self._page is other._page

    def same_context(self, other: "RoboPage") -> bool:
        """Return whether both pages belong to the same browser context."""
        return isinstance(other, RoboPage) and self._page.context is other._page.context

    def open_pages(self) -> list["RoboPage"]:
        """Return all open pages in this page's browser context."""
        return [
            type(self).get(page)
            for page in self._page.context.pages
            if not page.is_closed()
        ]

    def get_by_attributes(
        self,
        attributes: Mapping[str, Any],
        excat_match: bool | None = None,
    ) -> RoboLocator:
        """Return a ``RoboLocator`` found by arbitrary HTML attributes."""
        return self.locator_class.get_by_attributes(
            self._page,
            attributes=attributes,
            excat_match=excat_match,
        )

    def get_by_id(
        self,
        element_id: str,
        excat_match: bool | None = None,
    ) -> RoboLocator:
        """Return a ``RoboLocator`` found by HTML ``id``."""
        return self.locator_class.get_by_id(
            self._page,
            element_id=element_id,
            excat_match=excat_match,
        )
