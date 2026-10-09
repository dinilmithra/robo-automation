"""Pytest plugin for generic testcase correlation and per-test logging.

Application projects keep business-specific fixtures and reporting hooks in their own
code.  Installing ``robo-automation`` automatically supplies the cross-application
correlation lifecycle.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from collections.abc import Callable
from contextlib import nullcontext
from typing import Any, Iterator, Optional

import pytest
from playwright.sync_api import Browser, Error as PlaywrightError, Playwright, expect
from .config import (
    ArtifactPaths,
    DiagnosticsConfig,
    LoggingConfig,
    PerformanceConfig,
    RuntimeConfig,
)
from .correlation import bind_test_context, reset_test_context
from .logging import LogManager, LoggingService
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
    # Fixtures do not exist during pytest_configure. Resolve a minimal bootstrap
    # configuration from library defaults + environment and store it for the
    # fixture layer. Consumer fixture overrides take precedence once fixture
    # resolution begins.
    runtime_config = RuntimeConfig.from_env()
    config._robo_bootstrap_runtime_config = runtime_config
    LogManager.apply_bootstrap_config(config, runtime_config.logging, logger)

    collect_only = bool(getattr(config.option, "collectonly", False))
    numprocesses = int(getattr(config.option, "numprocesses", 0) or 0)
    if (
        not hasattr(config, "workerinput")
        and not collect_only
        and numprocesses > 0
        and runtime_config.performance.enabled
    ):
        os.environ.setdefault(
            "PERF_MONITOR_RUN_ID",
            f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}",
        )
        artifact_paths = ArtifactPaths.from_config(
            config.rootpath, runtime_config.artifacts
        )
        monitor = PytestPerformanceMonitor(
            config,
            performance_config=runtime_config.performance,
            artifact_paths=artifact_paths,
        )
        monitor.start()
        config._master_performance_monitor = monitor
        config._robo_performance_finalized = False
    expect.set_options(timeout=runtime_config.timeouts.wait_time_seconds * 1000)


def _finalize_controller_performance(config: pytest.Config) -> None:
    """Stop controller monitoring and merge worker summaries exactly once."""
    if hasattr(config, "workerinput") or bool(
        getattr(config, "_robo_performance_finalized", False)
    ):
        return
    monitor = getattr(config, "_master_performance_monitor", None)
    if monitor is not None:
        monitor.stop()
        config._master_performance_monitor = None
    runtime_config = getattr(
        config, "_robo_bootstrap_runtime_config", RuntimeConfig.from_env()
    )
    if runtime_config.performance.enabled:
        artifact_paths = ArtifactPaths.from_config(
            config.rootpath, runtime_config.artifacts
        )
        PytestPerformanceMonitor.merge_worker_summaries(
            artifact_paths.performance_logs,
            summary_limit=runtime_config.performance.summary_limit,
        )
    config._robo_performance_finalized = True


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Finalize generic controller performance after worker shutdown."""
    _finalize_controller_performance(session.config)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: pytest.Config) -> None:
    """Release generic runtime resources."""
    _finalize_controller_performance(config)
    LogManager.unconfigure_parallel_file_handler(config)
    LogManager.restore_record_factory()


# =========================================================================
# GENERIC TEST RESOURCE LIFECYCLE FIXTURES
# =========================================================================
@pytest.fixture(scope="session")
def robo_runtime_config(request: pytest.FixtureRequest) -> RuntimeConfig:
    """Return the resolved library runtime configuration.

    Consumers may override this fixture. If they do not, environment variables
    override immutable robo-automation defaults.
    """
    return getattr(
        request.config,
        "_robo_bootstrap_runtime_config",
        RuntimeConfig.from_env(),
    )


@pytest.fixture(scope="session")
def robo_logging_config(robo_runtime_config: RuntimeConfig) -> LoggingConfig:
    """Expose logging configuration as a consumer-overridable fixture."""
    return robo_runtime_config.logging


@pytest.fixture(scope="session")
def robo_diagnostics_config(
    robo_runtime_config: RuntimeConfig,
) -> DiagnosticsConfig:
    """Expose browser diagnostic configuration as a consumer-overridable fixture."""
    return robo_runtime_config.diagnostics


@pytest.fixture(scope="session")
def robo_performance_config(
    robo_runtime_config: RuntimeConfig,
) -> PerformanceConfig:
    """Expose performance configuration as a consumer-overridable fixture."""
    return robo_runtime_config.performance


@pytest.fixture(scope="session")
def robo_artifact_paths(
    request: pytest.FixtureRequest,
    robo_runtime_config: RuntimeConfig,
) -> ArtifactPaths:
    """Resolve all generic artifact paths once for the consumer project."""
    return ArtifactPaths.from_config(
        request.config.rootpath, robo_runtime_config.artifacts
    )


@pytest.fixture(scope="session")
def robo_logging_service(
    robo_logging_config: LoggingConfig,
    robo_artifact_paths: ArtifactPaths,
) -> LoggingService:
    """Construct the session/worker logging service from resolved fixtures."""
    return LoggingService(robo_logging_config, robo_artifact_paths, logger)


@pytest.fixture(scope="session", autouse=True)
def robo_logging_runtime(
    request: pytest.FixtureRequest,
    robo_logging_service: LoggingService,
) -> Iterator[None]:
    """Apply runtime logging after consumer fixture overrides are resolved."""
    if not bool(getattr(request.config.option, "collectonly", False)):
        robo_logging_service.start_session(request.config)
    try:
        yield
    finally:
        robo_logging_service.stop_session(request.config)


@pytest.fixture(scope="session", autouse=True)
def robo_runtime_timeout(
    wait_time: int,
) -> None:
    """Apply fixture-resolved timeout configuration to Playwright expectations."""
    expect.set_options(timeout=wait_time * 1000)


@pytest.fixture(scope="session", autouse=True)
def performance_monitor(
    request: pytest.FixtureRequest,
    robo_performance_config: PerformanceConfig,
    robo_artifact_paths: ArtifactPaths,
) -> Iterator[Optional[PytestPerformanceMonitor]]:
    """Provide one generic performance monitor per pytest/xdist worker."""
    yield from performance_monitor_lifecycle(
        request, robo_performance_config, robo_artifact_paths
    )


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
                    logger.warning(
                        "Unable to explicitly close browser context: %s", exc
                    )


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
def wait_time(robo_runtime_config: RuntimeConfig) -> int:
    """Return the resolved operation/navigation timeout in seconds.

    Consumers may still override this fixture directly; otherwise WAIT_TIME
    overrides the library default through ``robo_runtime_config``.
    """
    return robo_runtime_config.timeouts.wait_time_seconds


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


@pytest.fixture(autouse=True)
def robo_testcase_logging(
    request: pytest.FixtureRequest,
    robo_logging_runtime: None,
    robo_logging_service: LoggingService,
) -> Iterator[None]:
    """Own per-test log handlers using fixture-resolved configuration."""
    item = request.node
    robo_logging_service.start_testcase(item)
    logger.info(
        "TESTCASE START nodeid=%s testcase_id=%s process_id=%s attempt=%s",
        item.nodeid,
        getattr(item, "_robo_test_case_id", "-"),
        getattr(item, "_robo_process_id", "-"),
        getattr(item, "_robo_attempt_id", "-"),
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
            getattr(item, "_robo_test_case_id", "-"),
            getattr(item, "_robo_process_id", "-"),
            getattr(item, "_robo_attempt_id", "-"),
            outcome,
        )
        robo_logging_service.stop_testcase(item)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None):
    """Bind one testcase/process/attempt ID for setup, call, and teardown."""
    tokens = bind_test_context(item)
    try:
        yield
    finally:
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
