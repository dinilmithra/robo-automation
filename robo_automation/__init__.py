"""Generic Playwright/pytest automation utilities."""

from .correlation import (
    bind_test_context,
    build_attempt_id,
    build_process_id,
    build_test_case_id,
    current_correlation,
    reset_test_context,
)
from .logging import LogManager
from .performance import PytestPerformanceMonitor

__all__ = [
    "LogManager",
    "PytestPerformanceMonitor",
    "bind_test_context",
    "build_attempt_id",
    "build_process_id",
    "build_test_case_id",
    "current_correlation",
    "reset_test_context",
]
