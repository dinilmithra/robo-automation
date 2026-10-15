"""Playwright Page wrapper used by consuming browser automation projects."""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Mapping, Pattern

from playwright.sync_api import Error as PlaywrightError, Locator, Page

from robo_automation.errors import RoboNavigationError
from robo_automation.snapshot_evidence import ensure_snapshot_service

from robo_automation.framework.robo_locator import RoboLocator

logger = logging.getLogger(__name__)

_NAVIGATION_ATTEMPTS = 3
_NAVIGATION_RECOVERY_TIMEOUT_MS = 3000
_CHROME_ERROR_PREFIX = "chrome-error://"


def _is_transient_chrome_navigation_error(message: str, current_url: str) -> bool:
    """Return whether Chromium temporarily replaced a navigation with its error page."""
    normalized = message.lower()
    return (
        current_url.startswith(_CHROME_ERROR_PREFIX)
        or "chrome-error://chromewebdata/" in normalized
        or (
            "interrupted by another navigation" in normalized
            and "chrome-error://" in normalized
        )
    )


class RoboPage:
    """Own a Playwright ``Page`` behind the browser automation framework boundary."""

    locator_class: type[RoboLocator] = RoboLocator

    def __init__(self, page: Page) -> None:
        if not isinstance(page, Page):
            raise TypeError("RoboPage requires a Playwright Page.")
        # Snapshot activation must not depend solely on pytest fixture ordering.
        # This process-local guard is idempotent and is especially important for
        # xdist workers, where each worker owns its own Playwright runtime.
        ensure_snapshot_service()
        self._page = page

    @classmethod
    def get(cls, page: Page | "RoboPage") -> "RoboPage":
        """Wrap a Playwright ``Page`` without hiding its native API."""
        if isinstance(page, cls):
            return page
        if isinstance(page, RoboPage):
            page = page._page
        return cls(page)

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the wrapped Playwright page.

        RoboPage adds framework behavior; it does not intentionally hide any
        standard Playwright Page attribute or method.
        """
        return getattr(self._page, name)

    def __dir__(self) -> list[str]:
        """Include Playwright Page members in runtime introspection."""
        return sorted(set(super().__dir__()) | set(dir(self._page)))

    def specialize(self, page_type: type[Any]) -> Any:
        """Wrap this page with a higher-level page type.

        RoboPage subclasses continue to work, while composition-based wrappers
        such as ``AppianPage`` can expose ``get(RoboPage)`` without requiring
        robo-automation to import the higher-level package.
        """
        if isinstance(self, page_type):
            return self
        get = getattr(page_type, "get", None)
        if not callable(get):
            raise TypeError("page_type must provide a callable get() factory.")
        return get(self)

    @property
    def url(self) -> str:
        """Return the current page URL."""
        return self._page.url

    @property
    def main_frame(self):
        """Return the current main frame for event/diagnostic comparison."""
        return self._page.main_frame

    def goto(self, url: str, **kwargs: Any):
        """Navigate to ``url`` with bounded recovery for Chromium's transient error page.

        Chromium can occasionally interrupt an otherwise valid navigation by briefly
        replacing the target with ``chrome-error://chromewebdata/``.  This is most
        visible when several xdist workers start browsers at the same time.  Recover
        only that confirmed transient condition; all other browser errors fail
        immediately.
        """
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "serial")
        errors: list[str] = []

        for attempt in range(1, _NAVIGATION_ATTEMPTS + 1):
            logger.info(
                "[%s] Navigation attempt %s/%s: %s",
                worker_id,
                attempt,
                _NAVIGATION_ATTEMPTS,
                url,
            )
            try:
                result = self._page.goto(url, **kwargs)
                if attempt > 1:
                    logger.info(
                        "[%s] Navigation succeeded on attempt %s/%s: %s",
                        worker_id,
                        attempt,
                        _NAVIGATION_ATTEMPTS,
                        url,
                    )
                return result
            except PlaywrightError as exc:
                message = str(exc)
                current_url = self._page.url
                errors.append(message)

                if not _is_transient_chrome_navigation_error(message, current_url):
                    code = (
                        "ROBO_NAVIGATION_ABORTED"
                        if "ERR_ABORTED" in message
                        else "ROBO_NAVIGATION_ERROR"
                    )
                    raise RoboNavigationError(
                        f"Navigation failed for {url}: {message}",
                        code=code,
                        details={
                            "url": url,
                            "browser_error": message,
                            "attempt": attempt,
                            "worker": worker_id,
                        },
                    ) from exc

                logger.warning(
                    "[%s] Transient Chromium error-page navigation detected "
                    "on attempt %s/%s for %s.",
                    worker_id,
                    attempt,
                    _NAVIGATION_ATTEMPTS,
                    url,
                )

                if attempt >= _NAVIGATION_ATTEMPTS:
                    raise RoboNavigationError(
                        f"Navigation failed for {url} after "
                        f"{_NAVIGATION_ATTEMPTS} attempts: {message}",
                        code="ROBO_NAVIGATION_TRANSIENT_EXHAUSTED",
                        details={
                            "url": url,
                            "browser_error": message,
                            "attempts": _NAVIGATION_ATTEMPTS,
                            "worker": worker_id,
                            "browser_errors": errors,
                        },
                    ) from exc

                # Chromium sometimes recovers from its internal error page on its own.
                # Wait on that observable state instead of sleeping.  If it recovers,
                # the requested navigation is already progressing and must not be
                # interrupted by another goto().
                if current_url.startswith(_CHROME_ERROR_PREFIX):
                    try:
                        self._page.wait_for_url(
                            lambda value: not str(value).startswith(
                                _CHROME_ERROR_PREFIX
                            ),
                            timeout=_NAVIGATION_RECOVERY_TIMEOUT_MS,
                        )
                    except PlaywrightError:
                        pass
                    else:
                        logger.info(
                            "[%s] Navigation recovered from Chromium error page: %s",
                            worker_id,
                            self._page.url,
                        )
                        return None

        raise AssertionError("Unreachable navigation retry state.")

    def reload(self, **kwargs: Any):
        """Reload the current page and translate browser-engine failures."""
        try:
            return self._page.reload(**kwargs)
        except PlaywrightError as exc:
            message = str(exc)
            raise RoboNavigationError(
                f"Page reload failed: {message}",
                code="ROBO_RELOAD_ERROR",
                details={"url": self.url, "browser_error": message},
            ) from exc

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


def is_framework_page(value: object) -> bool:
    """Return whether ``value`` is or wraps a robo-automation page.

    Higher-level transparent wrappers can expose a ``robo_page`` property
    without requiring robo-automation to import the higher-level package.
    """
    if isinstance(value, RoboPage):
        return True
    try:
        return isinstance(getattr(value, "robo_page"), RoboPage)
    except (AttributeError, TypeError):
        return False
