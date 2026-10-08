"""Typed configuration for reusable automation runtime infrastructure.

Resolution precedence is intentionally simple:

1. A consumer can override the public pytest configuration fixture.
2. Otherwise environment variables override library defaults.
3. Otherwise the immutable library defaults are used.

Only this module reads automation configuration environment variables. Runtime
services consume resolved configuration objects instead of reaching into
``os.environ`` themselves.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


_TRUE_VALUES = {"1", "true", "yes", "y", "on"}


def _env_string(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return default if value is None else str(value)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return bool(default)
    return str(value).strip().lower() in _TRUE_VALUES


def _env_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return int(default)
    try:
        return int(str(value).strip())
    except ValueError:
        return int(default)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return float(default)
    try:
        return float(str(value).strip())
    except ValueError:
        return float(default)


def _optional_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return None
    return str(value)


@dataclass(frozen=True)
class LoggingConfig:
    """Logging defaults and environment-backed overrides."""

    level: str = "INFO"
    cli_level: Optional[str] = None
    cli_format: Optional[str] = None
    cli_date_format: Optional[str] = None
    parallel_file_enabled: bool = False
    testcase_file_enabled: bool = True

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        defaults = cls()
        return cls(
            level=_env_string("PYTEST_LOG_LEVEL", defaults.level),
            cli_level=_optional_env("PYTEST_LOG_CLI_LEVEL"),
            cli_format=_optional_env("PYTEST_LOG_CLI_FORMAT"),
            cli_date_format=_optional_env("PYTEST_LOG_CLI_DATE_FORMAT"),
            parallel_file_enabled=_env_bool(
                "PYTEST_PARALLEL_LOG_TO_FILE", defaults.parallel_file_enabled
            ),
            testcase_file_enabled=_env_bool(
                "TESTCASE_LOG_ENABLED", defaults.testcase_file_enabled
            ),
        )


@dataclass(frozen=True)
class ArtifactConfig:
    """Artifact locations relative to the consumer pytest root by default."""

    root: str = "artifacts"
    execution_logs: str = "artifacts/logs/execution"
    testcase_logs: str = "artifacts/logs/testcases"
    performance_logs: str = "artifacts/logs/performance"
    browser_diagnostics: str = "artifacts/browser-actions"
    failure_evidence: str = "artifacts/evidence/failures"

    @classmethod
    def from_env(cls) -> "ArtifactConfig":
        defaults = cls()
        root = _env_string("ARTIFACTS_ROOT", defaults.root)
        return cls(
            root=root,
            execution_logs=_env_string(
                "PYTEST_PARALLEL_LOG_PATH", defaults.execution_logs
            ),
            testcase_logs=_env_string("TESTCASE_LOG_PATH", defaults.testcase_logs),
            performance_logs=_env_string(
                "PERF_MONITOR_PATH", defaults.performance_logs
            ),
            browser_diagnostics=_env_string(
                "BROWSER_DIAGNOSTICS_PATH", defaults.browser_diagnostics
            ),
            failure_evidence=_env_string(
                "FAILURE_EVIDENCE_PATH", defaults.failure_evidence
            ),
        )


@dataclass(frozen=True)
class ArtifactPaths:
    """Resolved absolute artifact paths used by runtime services."""

    root: Path
    execution_logs: Path
    testcase_logs: Path
    performance_logs: Path
    browser_diagnostics: Path
    failure_evidence: Path

    @staticmethod
    def _resolve(rootpath: Path, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else rootpath / path

    @classmethod
    def from_config(
        cls, rootpath: Path, config: ArtifactConfig
    ) -> "ArtifactPaths":
        rootpath = Path(rootpath)
        return cls(
            root=cls._resolve(rootpath, config.root),
            execution_logs=cls._resolve(rootpath, config.execution_logs),
            testcase_logs=cls._resolve(rootpath, config.testcase_logs),
            performance_logs=cls._resolve(rootpath, config.performance_logs),
            browser_diagnostics=cls._resolve(rootpath, config.browser_diagnostics),
            failure_evidence=cls._resolve(rootpath, config.failure_evidence),
        )


@dataclass(frozen=True)
class DiagnosticsConfig:
    """Generic browser diagnostic feature controls."""

    enabled: bool = False
    capture_console: bool = True
    capture_page_errors: bool = True
    capture_network: bool = True
    capture_navigation: bool = True

    @classmethod
    def from_env(cls) -> "DiagnosticsConfig":
        defaults = cls()
        return cls(
            enabled=_env_bool("ENABLE_BROWSER_DIAGNOSTICS", defaults.enabled),
            capture_console=_env_bool(
                "BROWSER_DIAGNOSTICS_CONSOLE", defaults.capture_console
            ),
            capture_page_errors=_env_bool(
                "BROWSER_DIAGNOSTICS_PAGE_ERRORS", defaults.capture_page_errors
            ),
            capture_network=_env_bool(
                "BROWSER_DIAGNOSTICS_NETWORK", defaults.capture_network
            ),
            capture_navigation=_env_bool(
                "BROWSER_DIAGNOSTICS_NAVIGATION", defaults.capture_navigation
            ),
        )


@dataclass(frozen=True)
class PerformanceConfig:
    """Performance monitoring configuration."""

    enabled: bool = True
    actions_enabled: bool = True
    framework_enabled: bool = True
    console_enabled: bool = False
    sample_interval: float = 1.0
    flush_every: int = 20
    threshold_ms: float = 500.0
    slow_ms: float = 2000.0
    summary_limit: int = 50
    run_id: str = "run-unknown"

    @classmethod
    def from_env(cls) -> "PerformanceConfig":
        defaults = cls()
        return cls(
            enabled=_env_bool("PERF_MONITOR_ENABLED", defaults.enabled),
            actions_enabled=_env_bool(
                "PERF_MONITOR_ACTIONS", defaults.actions_enabled
            ),
            framework_enabled=_env_bool(
                "PERF_MONITOR_FRAMEWORK", defaults.framework_enabled
            ),
            console_enabled=_env_bool(
                "PERF_MONITOR_CONSOLE", defaults.console_enabled
            ),
            sample_interval=max(
                0.1,
                _env_float("PERF_MONITOR_INTERVAL", defaults.sample_interval),
            ),
            flush_every=max(
                1, _env_int("PERF_MONITOR_FLUSH_EVERY", defaults.flush_every)
            ),
            threshold_ms=max(
                0.0, _env_float("PERF_MONITOR_THRESHOLD_MS", defaults.threshold_ms)
            ),
            slow_ms=max(
                0.0, _env_float("PERF_MONITOR_SLOW_MS", defaults.slow_ms)
            ),
            summary_limit=max(
                1, _env_int("PERF_MONITOR_SUMMARY_LIMIT", defaults.summary_limit)
            ),
            run_id=_env_string("PERF_MONITOR_RUN_ID", defaults.run_id),
        )


@dataclass(frozen=True)
class TimeoutConfig:
    """Generic operation timeout settings."""

    wait_time_seconds: int = 90

    @classmethod
    def from_env(cls) -> "TimeoutConfig":
        defaults = cls()
        return cls(
            wait_time_seconds=max(
                1, _env_int("WAIT_TIME", defaults.wait_time_seconds)
            )
        )


@dataclass(frozen=True)
class RuntimeConfig:
    """Composition root for reusable robo-automation configuration."""

    logging: LoggingConfig
    artifacts: ArtifactConfig
    diagnostics: DiagnosticsConfig
    performance: PerformanceConfig
    timeouts: TimeoutConfig

    @classmethod
    def defaults(cls) -> "RuntimeConfig":
        return cls(
            logging=LoggingConfig(),
            artifacts=ArtifactConfig(),
            diagnostics=DiagnosticsConfig(),
            performance=PerformanceConfig(),
            timeouts=TimeoutConfig(),
        )

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        return cls(
            logging=LoggingConfig.from_env(),
            artifacts=ArtifactConfig.from_env(),
            diagnostics=DiagnosticsConfig.from_env(),
            performance=PerformanceConfig.from_env(),
            timeouts=TimeoutConfig.from_env(),
        )


class AutomationConfig:
    """Backward-compatible environment API for external consumers.

    New robo-automation runtime code should consume the typed configuration
    objects above. This facade remains for compatibility with existing users.
    """

    get_env_string = staticmethod(_env_string)
    get_env_bool = staticmethod(_env_bool)
    get_env_int = staticmethod(_env_int)

    @staticmethod
    def get_project_root() -> Path:
        return Path.cwd()
