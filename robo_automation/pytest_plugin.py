"""Pytest plugin for generic testcase correlation and per-test logging.

Application projects keep business-specific fixtures and reporting hooks in their own
code.  Installing ``robo-automation`` automatically supplies the cross-application
correlation lifecycle.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import nullcontext
from typing import Any, Iterator, Optional

import pytest
from playwright.sync_api import Browser, Error as PlaywrightError, Playwright, expect
from .config import AutomationConfig
from .correlation import bind_test_context, reset_test_context
from .logging import LogManager
from .browser import (
    browser_lifecycle,
    performance_monitor_lifecycle,
    playwright_lifecycle,
)
from .performance import PytestPerformanceMonitor
from .framework import RoboBrowserContext, RoboPage

logger = logging.getLogger(__name__)


class _GenericPageAliasPlugin:
    """Expose ``page`` only when no higher-level page plugin is installed."""

    @pytest.fixture
    def page(self, robo_page: RoboPage) -> RoboPage:
        """Return the generic ``RoboPage`` for standalone robo-automation use."""
        return robo_page


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    """Configure generic correlated logging for any application project."""
    pluginmanager = config.pluginmanager
    if (
        not pluginmanager.hasplugin("robo_appian")
        and not pluginmanager.hasplugin("robo_appian.pytest_plugin")
        and not pluginmanager.hasplugin("robo_automation_page_alias")
    ):
        pluginmanager.register(
            _GenericPageAliasPlugin(),
            name="robo_automation_page_alias",
        )
    LogManager.install_correlation_record_factory()
    LogManager.apply_log_level_from_env(config)
    LogManager.apply_log_cli_level_from_env(config, logger)
    LogManager.apply_log_cli_format_from_env(config)
    LogManager.apply_log_cli_date_format_from_env(config)
    expect.set_options(
        timeout=AutomationConfig.get_env_int("WAIT_TIME", 90) * 1000
    )
    if not bool(getattr(config.option, "collectonly", False)):
        LogManager.configure_worker_log_path(config, logger)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: pytest.Config) -> None:
    """Release generic logging resources."""
    LogManager.unconfigure_parallel_file_handler(config)
    LogManager.restore_record_factory()


# =========================================================================
# GENERIC TEST RESOURCE LIFECYCLE FIXTURES
# =========================================================================
@pytest.fixture(scope="session", autouse=True)
def performance_monitor(
    request: pytest.FixtureRequest,
) -> Iterator[Optional[PytestPerformanceMonitor]]:
    """Provide one generic performance monitor per pytest/xdist worker."""
    yield from performance_monitor_lifecycle(request)


@pytest.fixture(scope="session")
def robo_automation_playwright(
    performance_monitor: Optional[PytestPerformanceMonitor],
) -> Iterator[Playwright]:
    """Own the generic Playwright runtime for one pytest session."""
    yield from playwright_lifecycle(performance_monitor)


@pytest.fixture(scope="session")
def browser(
    robo_automation_playwright: Playwright,
    performance_monitor: Optional[PytestPerformanceMonitor],
    request: pytest.FixtureRequest,
) -> Iterator[Browser]:
    """Own the public raw Playwright browser for one pytest session/worker."""
    yield from browser_lifecycle(
        robo_automation_playwright, performance_monitor, request
    )


DEFAULT_WAIT_TIME = 90


def _measure_framework(
    performance_monitor: Optional[PytestPerformanceMonitor],
    action: str,
):
    """Return a timing context when performance monitoring is enabled."""
    if performance_monitor is None:
        return nullcontext()
    return performance_monitor.measure(action)


def _default_context_lifecycle(
    browser: Browser,
    context_options: dict[str, Any],
    performance_monitor: Optional[PytestPerformanceMonitor],
    wait_time: Optional[int],
    context_page_handler: Optional[Callable[[RoboPage], None]],
) -> Iterator[RoboBrowserContext]:
    """Create, configure, yield, and close one generic browser context."""
    context: Optional[RoboBrowserContext] = None
    try:
        with _measure_framework(performance_monitor, "browser_context_create"):
            context = RoboBrowserContext.get(browser.new_context(**context_options))

        if wait_time is not None:
            timeout_ms = wait_time * 1000
            context.set_default_timeout(timeout_ms)
            context.set_default_navigation_timeout(timeout_ms)

        if context_page_handler is not None:
            context.on("page", context_page_handler)

        yield context
    finally:
        if context is not None:
            try:
                with _measure_framework(performance_monitor, "browser_context_close"):
                    context.close()
            except PlaywrightError as exc:
                message = str(exc).lower()
                if "closed" not in message and "target" not in message:
                    logger.warning("Unable to explicitly close browser context: %s", exc)


def _default_page_lifecycle(
    context: RoboBrowserContext,
    performance_monitor: Optional[PytestPerformanceMonitor],
) -> Iterator[RoboPage]:
    """Create and close one generic ``RoboPage`` for the current test."""
    del performance_monitor
    page = context.new_page()
    try:
        yield page
    finally:
        page.close()


@pytest.fixture(scope="session")
def storage_state() -> None:
    """Provide an unauthenticated default storage state."""
    return None


@pytest.fixture
def context_options(storage_state: Any) -> dict[str, Any]:
    """Return generic options passed to ``Browser.new_context``."""
    options: dict[str, Any] = {}
    if storage_state:
        options["storage_state"] = storage_state
    return options


@pytest.fixture(scope="session")
def wait_time() -> int:
    """Return the generic operation/navigation timeout in seconds."""
    return DEFAULT_WAIT_TIME


@pytest.fixture
def context_page_handler() -> Optional[Callable[[RoboPage], None]]:
    """Return an optional callback invoked for each new page in a context."""
    return None


@pytest.fixture
def context(
    browser: Browser,
    context_options: dict[str, Any],
    performance_monitor: Optional[PytestPerformanceMonitor],
    wait_time: Optional[int],
    context_page_handler: Optional[Callable[[RoboPage], None]],
) -> Iterator[RoboBrowserContext]:
    """Provide a generic configured test-scoped ``RoboBrowserContext``."""
    yield from _default_context_lifecycle(
        browser, context_options, performance_monitor, wait_time, context_page_handler
    )


@pytest.fixture
def robo_page(
    context: RoboBrowserContext,
    performance_monitor: Optional[PytestPerformanceMonitor],
) -> Iterator[RoboPage]:
    """Own the generic test-scoped ``RoboPage`` lifecycle."""
    yield from _default_page_lifecycle(context, performance_monitor)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None):
    """Bind one testcase/process/attempt ID for setup, call, and teardown."""
    tokens = bind_test_context(item)
    log_path = LogManager.start_testcase_log(item)
    logger.info(
        "TESTCASE START nodeid=%s testcase_id=%s process_id=%s attempt=%s",
        item.nodeid,
        item._robo_test_case_id,
        item._robo_process_id,
        item._robo_attempt_id,
    )
    try:
        yield
    finally:
        phase_reports: dict[str, Any] = getattr(item, "phase_reports", {}) or {}
        outcome = "UNKNOWN"
        if any(getattr(r, "failed", False) for r in phase_reports.values()):
            outcome = "FAILED"
        elif any(getattr(r, "skipped", False) for r in phase_reports.values()):
            outcome = "SKIPPED"
        elif getattr(phase_reports.get("call"), "passed", False):
            outcome = "PASSED"
        logger.info(
            "TESTCASE END nodeid=%s testcase_id=%s process_id=%s attempt=%s outcome=%s",
            item.nodeid,
            item._robo_test_case_id,
            item._robo_process_id,
            item._robo_attempt_id,
            outcome,
        )
        LogManager.stop_testcase_log(item)
        reset_test_context(tokens)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):
    """Track generic setup/call/teardown outcomes for correlated end logging."""
    outcome = yield
    report = outcome.get_result()
    phase_reports = getattr(item, "phase_reports", None)
    if not isinstance(phase_reports, dict):
        phase_reports = {}
        item.phase_reports = phase_reports
    phase_reports[report.when] = report

