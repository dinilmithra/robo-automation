"""Generic Playwright/pytest automation utilities."""

from .correlation import (
    bind_test_context,
    build_attempt_id,
    build_process_id,
    build_test_case_id,
    current_correlation,
    reset_test_context,
)
from .logging import LogManager, LoggingService
from .config import (
    ArtifactConfig,
    ArtifactPaths,
    DiagnosticsConfig,
    LoggingConfig,
    PerformanceConfig,
    RuntimeConfig,
    TimeoutConfig,
)
from .performance import PytestPerformanceMonitor
from .framework import BrowserSession, RoboBrowserContext, RoboPage, RoboLocator, Scope

__all__ = [
    "LogManager",
    "LoggingService",
    "RuntimeConfig",
    "LoggingConfig",
    "ArtifactConfig",
    "ArtifactPaths",
    "DiagnosticsConfig",
    "PerformanceConfig",
    "TimeoutConfig",
    "PytestPerformanceMonitor",
    "BrowserSession",
    "RoboBrowserContext",
    "RoboPage",
    "RoboLocator",
    "Scope",
    "bind_test_context",
    "build_attempt_id",
    "build_process_id",
    "build_test_case_id",
    "current_correlation",
    "reset_test_context",
]
