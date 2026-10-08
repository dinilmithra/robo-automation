"""Reusable pytest/Python logging utilities with testcase correlation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from .config import ArtifactPaths, LoggingConfig
from .correlation import current_correlation


class LogManager:
    """Shared logging infrastructure used by pytest hooks and fixtures.

    Runtime methods accept resolved configuration objects. They intentionally do
    not read environment variables; configuration resolution belongs in
    ``robo_automation.config`` and the pytest configuration fixtures.
    """

    PARALLEL_LOG_HANDLER_ATTR = "_parallel_log_handler"
    TESTCASE_LOG_HANDLER_ATTR = "_robo_testcase_log_handler"
    TESTCASE_LOG_PATH_ATTR = "_robo_testcase_log_path"
    _ORIGINAL_RECORD_FACTORY = None
    PARALLEL_LOG_PATH_ATTR = "_parallel_log_path"
    VALID_LOG_LEVELS = {
        "CRITICAL",
        "ERROR",
        "WARNING",
        "INFO",
        "DEBUG",
        "NOTSET",
    }

    @staticmethod
    def _with_correlation_fields(format_string: str) -> str:
        value = str(format_string or "%(asctime)s - %(levelname)s - %(message)s")
        if "%(process_id)" in value:
            return value
        correlation = (
            "[TC=%(test_case_id)s] [PROCESS=%(process_id)s] [ATTEMPT=%(attempt_id)s]"
        )
        if "%(message)s" in value:
            return value.replace("%(message)s", f"{correlation} %(message)s", 1)
        return f"{value} {correlation}"

    @staticmethod
    def install_correlation_record_factory() -> None:
        if LogManager._ORIGINAL_RECORD_FACTORY is not None:
            return
        original = logging.getLogRecordFactory()
        LogManager._ORIGINAL_RECORD_FACTORY = original

        def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = original(*args, **kwargs)
            correlation = current_correlation()
            record.test_case_id = correlation["test_case_id"] or "-"
            record.process_id = correlation["process_id"] or "-"
            record.attempt_id = correlation["attempt_id"] or "-"
            return record

        logging.setLogRecordFactory(factory)

    @staticmethod
    def restore_record_factory() -> None:
        original = LogManager._ORIGINAL_RECORD_FACTORY
        if original is None:
            return
        logging.setLogRecordFactory(original)
        LogManager._ORIGINAL_RECORD_FACTORY = None

    @staticmethod
    def normalize_log_level(value: str) -> str:
        level = str(value or "").strip().upper()
        return "WARNING" if level == "WARN" else level

    @staticmethod
    def resolve_effective_log_level(
        config: Any,
        logger: logging.Logger,
        logging_config: Optional[LoggingConfig] = None,
    ) -> str:
        requested = LogManager.normalize_log_level(
            (logging_config or LoggingConfig()).level
        )
        if requested:
            if requested in LogManager.VALID_LOG_LEVELS:
                return requested
            logger.warning(
                "Ignoring invalid configured log level '%s'. Using pytest config level.",
                requested,
            )

        config_level = LogManager.normalize_log_level(
            str(getattr(config.option, "log_level", ""))
        )
        if config_level in LogManager.VALID_LOG_LEVELS:
            return config_level
        return "INFO"

    @staticmethod
    def apply_bootstrap_config(
        config: Any, logging_config: LoggingConfig, logger: logging.Logger
    ) -> None:
        """Apply early logging options before normal pytest fixtures exist."""
        level = LogManager.normalize_log_level(logging_config.level)
        if level in LogManager.VALID_LOG_LEVELS:
            config.option.log_level = level
        elif level:
            logger.warning("Ignoring invalid configured log level '%s'.", level)

        cli_level = LogManager.normalize_log_level(logging_config.cli_level or "")
        if cli_level:
            if cli_level in LogManager.VALID_LOG_LEVELS:
                config.option.log_cli_level = cli_level
            else:
                logger.warning("Ignoring invalid configured CLI log level '%s'.", cli_level)

        cli_format = logging_config.cli_format
        if cli_format:
            config.option.log_cli_format = LogManager._with_correlation_fields(cli_format)
            config.option.log_format = LogManager._with_correlation_fields(
                str(getattr(config.option, "log_format", "") or cli_format)
            )
        else:
            existing = str(getattr(config.option, "log_format", "") or "")
            if existing:
                config.option.log_format = LogManager._with_correlation_fields(existing)

        if logging_config.cli_date_format:
            config.option.log_cli_date_format = logging_config.cli_date_format

    @staticmethod
    def start_testcase_log(
        item: Any,
        logging_config: LoggingConfig,
        artifact_paths: ArtifactPaths,
    ) -> Optional[Path]:
        """Create a dedicated log file for the active testcase process ID."""
        if not logging_config.testcase_file_enabled:
            return None

        process_id = str(getattr(item, "_robo_process_id", "") or "unassigned")
        log_dir = artifact_paths.testcase_logs
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{process_id}.log"

        handler = logging.FileHandler(log_path, encoding="utf-8")
        effective_level = LogManager.resolve_effective_log_level(
            item.config, logging.getLogger(__name__), logging_config
        )
        handler.setLevel(getattr(logging, effective_level, logging.INFO))
        handler.setFormatter(
            logging.Formatter(
                LogManager._with_correlation_fields(
                    "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
                ),
                "%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger = logging.getLogger()
        if root_logger.level > handler.level:
            root_logger.setLevel(handler.level)
        root_logger.addHandler(handler)
        setattr(item, LogManager.TESTCASE_LOG_HANDLER_ATTR, handler)
        setattr(item, LogManager.TESTCASE_LOG_PATH_ATTR, str(log_path))
        return log_path

    @staticmethod
    def stop_testcase_log(item: Any) -> None:
        handler = getattr(item, LogManager.TESTCASE_LOG_HANDLER_ATTR, None)
        if handler is None:
            return
        root_logger = logging.getLogger()
        root_logger.removeHandler(handler)
        handler.close()
        setattr(item, LogManager.TESTCASE_LOG_HANDLER_ATTR, None)

    @staticmethod
    def configure_worker_log_path(
        config: Any,
        logger: logging.Logger,
        logging_config: LoggingConfig,
        artifact_paths: ArtifactPaths,
    ) -> None:
        """Route xdist logs to per-worker files when configured."""
        # Always remove a prior handler first. This makes fixture overrides
        # deterministic even if bootstrap configuration was different.
        LogManager.unconfigure_parallel_file_handler(config)
        if not logging_config.parallel_file_enabled:
            return

        is_worker = hasattr(config, "workerinput")
        numprocesses = int(getattr(config.option, "numprocesses", 0) or 0)
        if not is_worker and numprocesses <= 0:
            return

        worker_id = "master"
        if is_worker:
            worker_id = str(config.workerinput.get("workerid", "worker"))

        log_dir = artifact_paths.execution_logs
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"pytest-{worker_id}.log"
        effective_level = LogManager.resolve_effective_log_level(
            config, logger, logging_config
        )
        level_no = getattr(logging, effective_level, logging.INFO)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level_no)
        file_handler.setFormatter(
            logging.Formatter(
                LogManager._with_correlation_fields(
                    "%(asctime)s [%(levelname)s] [%(processName)s:%(process)d] [%(name)s] %(message)s"
                ),
                "%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        if root_logger.level > level_no:
            root_logger.setLevel(level_no)

        setattr(config, LogManager.PARALLEL_LOG_HANDLER_ATTR, file_handler)
        setattr(config, LogManager.PARALLEL_LOG_PATH_ATTR, log_path)
        role = worker_id if worker_id != "master" else "master"
        logger.info("Parallel logging enabled for %s; writing to %s", role, log_path)

    @staticmethod
    def unconfigure_parallel_file_handler(config: Any) -> None:
        handler = getattr(config, LogManager.PARALLEL_LOG_HANDLER_ATTR, None)
        if handler is None:
            return
        root_logger = logging.getLogger()
        root_logger.removeHandler(handler)
        handler.close()
        setattr(config, LogManager.PARALLEL_LOG_HANDLER_ATTR, None)


class LoggingService:
    """Instance-owned logging lifecycle for one pytest session/worker.

    ``LogManager`` remains as a compatibility/implementation facade, while new
    runtime code receives this service through the ``robo_logging_service``
    fixture. Keeping configuration on the instance avoids global environment
    reads and makes per-worker/consumer overrides explicit.
    """

    def __init__(
        self,
        config: LoggingConfig,
        artifact_paths: ArtifactPaths,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config
        self.artifact_paths = artifact_paths
        self.logger = logger or logging.getLogger(__name__)

    def start_session(self, pytest_config: Any) -> None:
        LogManager.apply_bootstrap_config(pytest_config, self.config, self.logger)
        LogManager.configure_worker_log_path(
            pytest_config,
            self.logger,
            self.config,
            self.artifact_paths,
        )

    def stop_session(self, pytest_config: Any) -> None:
        LogManager.unconfigure_parallel_file_handler(pytest_config)

    def start_testcase(self, item: Any) -> Optional[Path]:
        return LogManager.start_testcase_log(item, self.config, self.artifact_paths)

    def stop_testcase(self, item: Any) -> None:
        LogManager.stop_testcase_log(item)
