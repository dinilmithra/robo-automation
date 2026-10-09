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
from .action_snapshots import ActionSnapshotMonitor
from .errors import RoboAutomationError, RoboNavigationError
from .config import (
    ActionSnapshotConfig,
    ArtifactConfig,
    ArtifactPaths,
    DiagnosticsConfig,
    LoggingConfig,
    PerformanceConfig,
    RuntimeConfig,
    TimeoutConfig,
)
from .performance import PytestPerformanceMonitor
from .framework import BrowserSession, RoboBrowserContext, RoboPage, RoboLocator, Scope, is_framework_page

__all__ = [
    "RoboAutomationError",
    "RoboNavigationError",
    "LogManager",
    "LoggingService",
    "RuntimeConfig",
    "LoggingConfig",
    "ActionSnapshotConfig",
    "ActionSnapshotMonitor",
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
    "is_framework_page",
    "bind_test_context",
    "build_attempt_id",
    "build_process_id",
    "build_test_case_id",
    "current_correlation",
    "reset_test_context",
]
