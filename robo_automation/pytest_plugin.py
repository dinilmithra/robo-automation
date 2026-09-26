"""Pytest plugin for generic testcase correlation and per-test logging.

Application projects keep business-specific fixtures and reporting hooks in their own
code.  Installing ``robo-automation`` automatically supplies the cross-application
correlation lifecycle.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator, Optional

import pytest
from playwright.sync_api import Browser, Playwright, expect
from .config import AutomationConfig
from .correlation import bind_test_context, reset_test_context
from .logging import LogManager
from .browser import (
    browser_lifecycle,
    performance_monitor_lifecycle,
    playwright_lifecycle,
)
from .performance import PytestPerformanceMonitor

logger = logging.getLogger(__name__)


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    """Configure generic correlated logging for any application project."""
    LogManager.install_correlation_record_factory()
    LogManager.apply_log_level_from_env(config)
    LogManager.apply_log_cli_level_from_env(config, logger)
    LogManager.apply_log_cli_format_from_env(config)
    LogManager.apply_log_cli_date_format_from_env(config)
    expect.set_options(
        timeout=AutomationConfig.get_env_int("WAIT_TIME", 180) * 1000
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
def playwright(
    performance_monitor: Optional[PytestPerformanceMonitor],
) -> Iterator[Playwright]:
    """Own the generic Playwright runtime for one pytest session."""
    yield from playwright_lifecycle(performance_monitor)


@pytest.fixture(scope="session")
def browser(
    playwright: Playwright,
    performance_monitor: Optional[PytestPerformanceMonitor],
    request: pytest.FixtureRequest,
) -> Iterator[Browser]:
    """Own the configured generic browser for one pytest session/worker."""
    yield from browser_lifecycle(playwright, performance_monitor, request)


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

