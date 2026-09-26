"""Generic Playwright browser lifecycle utilities."""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional

import pytest
from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright

from .config import AutomationConfig
from .performance import PytestPerformanceMonitor

logger = logging.getLogger(__name__)


def _measure(monitor: Optional[PytestPerformanceMonitor], action: str, **metadata: Any):
    if monitor is None:
        return nullcontext()
    return monitor.measure(action, metadata=metadata or None)


def close_resource(resource: Any, label: str) -> None:
    """Close a Playwright resource without masking an earlier test failure."""
    try:
        resource.close()
    except Exception as exc:  # pragma: no cover - defensive cleanup
        logger.warning("Unable to close %s cleanly: %s", label, exc)


def performance_monitor_lifecycle(
    request: pytest.FixtureRequest,
) -> Iterator[Optional[PytestPerformanceMonitor]]:
    """Start one performance monitor per pytest/xdist worker when enabled."""
    if not AutomationConfig.get_env_bool("PERF_MONITOR_ENABLED", True):
        yield None
        return
    monitor = PytestPerformanceMonitor(request.config)
    monitor.start()
    request.config._performance_monitor = monitor
    try:
        yield monitor
    finally:
        request.config._performance_monitor = None
        monitor.stop()


def playwright_lifecycle(
    performance_monitor: Optional[PytestPerformanceMonitor],
) -> Iterator[Playwright]:
    """Start and stop Playwright for one pytest session."""
    manager = sync_playwright()
    with _measure(performance_monitor, "playwright_start"):
        instance = manager.start()
    try:
        yield instance
    finally:
        with _measure(performance_monitor, "playwright_stop"):
            instance.stop()


def _launch_browser_in_slot(
    config: pytest.Config,
    worker_id: str,
    browser_type: Any,
    *,
    headless: bool,
) -> Browser:
    timeout_ms = AutomationConfig.get_env_int("WAIT_TIME", 180) * 1000

    def launch() -> Browser:
        logger.info("Launching browser for %s.", worker_id)
        instance = browser_type.launch(headless=headless, timeout=timeout_ms)
        logger.info("Browser launched successfully for %s.", worker_id)
        return instance

    if not AutomationConfig.get_env_bool("ENABLE_BROWSER_LAUNCH_DELAY", False):
        return launch()
    interval = max(0, AutomationConfig.get_env_int("BROWSER_LAUNCH_INTERVAL_SECONDS", 0))
    if interval == 0:
        return launch()

    cache_path = Path(AutomationConfig.get_env_string("CACHE_PATH", "artifacts/runtime/cache"))
    if not cache_path.is_absolute():
        cache_path = Path(config.rootpath) / cache_path
    cache_path.mkdir(parents=True, exist_ok=True)
    state_path = cache_path / "browser-launch.timestamp"
    lock_path = cache_path / "browser-launch.lock"
    lock_timeout = max(AutomationConfig.get_env_int("WAIT_TIME", 180), 60)
    started = time.monotonic()
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except (FileExistsError, PermissionError):
            try:
                if time.time() - lock_path.stat().st_mtime > lock_timeout:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.monotonic() - started >= lock_timeout:
                raise TimeoutError(f"Timed out waiting for browser launch gate: {lock_path}")
            threading.Event().wait(0.1)
    try:
        last_launch = 0.0
        try:
            last_launch = float(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        delay = max(0.0, interval - (time.time() - last_launch))
        if delay:
            threading.Event().wait(delay)
        instance = launch()
        temp_path = state_path.with_name(f".{state_path.name}.{os.getpid()}.tmp")
        temp_path.write_text(str(time.time()), encoding="utf-8")
        os.replace(temp_path, state_path)
        return instance
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def browser_lifecycle(
    playwright: Playwright,
    performance_monitor: Optional[PytestPerformanceMonitor],
    request: pytest.FixtureRequest,
) -> Iterator[Browser]:
    """Create and close a configured session browser."""
    headless = AutomationConfig.get_env_bool("HEAD_LESS", True)
    browser_name = AutomationConfig.get_env_string("BROWSER", "chromium").lower()
    browser_type = getattr(playwright, browser_name, playwright.chromium)
    worker_id = str(getattr(request.config, "workerinput", {}).get("workerid", ""))
    with _measure(performance_monitor, "browser_launch", browser=browser_name, headless=headless):
        browser = _launch_browser_in_slot(
            request.config, worker_id or "serial", browser_type, headless=headless
        )
    try:
        yield browser
    finally:
        with _measure(performance_monitor, "browser_close"):
            close_resource(browser, "browser")


def context_lifecycle(
    browser: Browser,
    storage_state: Optional[Dict[str, Any]],
    performance_monitor: Optional[PytestPerformanceMonitor],
    *,
    on_page: Optional[Callable[[Any], None]] = None,
) -> Iterator[BrowserContext]:
    """Create and close a browser context, optionally using authenticated state."""
    headless = AutomationConfig.get_env_bool("HEAD_LESS", True)
    options: Dict[str, Any] = {"ignore_https_errors": True}
    if storage_state:
        options["storage_state"] = storage_state
    if not headless:
        options["no_viewport"] = True
    with _measure(performance_monitor, "browser_context_create"):
        context = browser.new_context(**options)
        timeout_ms = AutomationConfig.get_env_int("WAIT_TIME", 180) * 1000
        context.set_default_timeout(timeout_ms)
        context.set_default_navigation_timeout(timeout_ms)
        if on_page is not None:
            context.on("page", on_page)
    try:
        yield context
    finally:
        with _measure(performance_monitor, "browser_context_close"):
            close_resource(context, "browser context")
