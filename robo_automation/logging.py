"""Reusable pytest/Python logging utilities with testcase correlation."""

import logging
from pathlib import Path
from typing import Any

from .correlation import current_correlation
from .config import AutomationConfig


class LogManager:
    """Shared logging helpers used by pytest hooks."""

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
        """Ensure a logging format renders testcase/process correlation IDs."""
        value = str(format_string or "%(asctime)s - %(levelname)s - %(message)s")
        if "%(process_id)" in value:
            return value
        correlation = "[TC=%(test_case_id)s] [PROCESS=%(process_id)s] [ATTEMPT=%(attempt_id)s]"
        if "%(message)s" in value:
            return value.replace("%(message)s", f"{correlation} %(message)s", 1)
        return f"{value} {correlation}"

    @staticmethod
    def install_correlation_record_factory() -> None:
        """Inject correlation attributes into every Python LogRecord."""
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
        """Restore the LogRecord factory that existed before robo-automation configured logging."""
        original = LogManager._ORIGINAL_RECORD_FACTORY
        if original is None:
            return
        logging.setLogRecordFactory(original)
        LogManager._ORIGINAL_RECORD_FACTORY = None

    @staticmethod
    def start_testcase_log(item: Any) -> Path:
        """Create a dedicated log file for the active testcase process ID."""
        process_id = str(getattr(item, "_robo_process_id", "") or "unassigned")
        configured = AutomationConfig.get_env_string(
            "TESTCASE_LOG_PATH", "artifacts/logs/testcases"
        )
        log_dir = Path(configured)
        if not log_dir.is_absolute():
            log_dir = Path(item.config.rootpath) / log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{process_id}.log"

        handler = logging.FileHandler(log_path, encoding="utf-8")
        effective_level = LogManager.resolve_effective_log_level(item.config, logging.getLogger(__name__))
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
        item._robo_testcase_log_handler = handler
        item._robo_testcase_log_path = str(log_path)
        return log_path

    @staticmethod
    def stop_testcase_log(item: Any) -> None:
        """Close the dedicated testcase log handler."""
        handler = getattr(item, LogManager.TESTCASE_LOG_HANDLER_ATTR, None)
        if handler is None:
            return
        root_logger = logging.getLogger()
        root_logger.removeHandler(handler)
        handler.close()
        setattr(item, LogManager.TESTCASE_LOG_HANDLER_ATTR, None)

    @staticmethod
    def normalize_log_level(value: str) -> str:
        """Normalize a log-level name and expand the WARN alias."""
        level = value.strip().upper()
        return "WARNING" if level == "WARN" else level

    @staticmethod
    def resolve_effective_log_level(config: Any, logger: logging.Logger) -> str:
        """Resolve the effective log level from environment and pytest settings."""
        env_level = LogManager.normalize_log_level(
            AutomationConfig.get_env_string("PYTEST_LOG_LEVEL", "")
        )
        if env_level:
            if env_level in LogManager.VALID_LOG_LEVELS:
                return env_level
            logger.warning(
                "Ignoring invalid PYTEST_LOG_LEVEL='%s'. Using pytest config level.",
                env_level,
            )

        config_level = LogManager.normalize_log_level(
            str(getattr(config.option, "log_level", ""))
        )
        if config_level in LogManager.VALID_LOG_LEVELS:
            return config_level
        return "INFO"

    @staticmethod
    def apply_log_level_from_env(config: Any) -> None:
        """Apply a valid environment log level to pytest configuration."""
        env_level = LogManager.normalize_log_level(
            AutomationConfig.get_env_string("PYTEST_LOG_LEVEL", "")
        )
        if env_level in LogManager.VALID_LOG_LEVELS:
            config.option.log_level = env_level

    @staticmethod
    def apply_log_cli_level_from_env(config: Any, logger: logging.Logger) -> None:
        """Apply a valid environment console log level to pytest configuration."""
        env_level = LogManager.normalize_log_level(
            AutomationConfig.get_env_string("PYTEST_LOG_CLI_LEVEL", "")
        )
        if not env_level:
            return

        if env_level in LogManager.VALID_LOG_LEVELS:
            config.option.log_cli_level = env_level
            return

        logger.warning(
            "Ignoring invalid PYTEST_LOG_CLI_LEVEL='%s'.",
            env_level,
        )

    @staticmethod
    def apply_log_cli_format_from_env(config: Any) -> None:
        """Apply the configured console log format to pytest."""
        cli_format = AutomationConfig.get_env_string("PYTEST_LOG_CLI_FORMAT", "")
        config.option.log_cli_format = LogManager._with_correlation_fields(cli_format)
        config.option.log_format = LogManager._with_correlation_fields(
            str(getattr(config.option, "log_format", "") or cli_format)
        )

    @staticmethod
    def apply_log_cli_date_format_from_env(config: Any) -> None:
        """Apply the configured console date format to pytest."""
        cli_date_format = AutomationConfig.get_env_string("PYTEST_LOG_CLI_DATE_FORMAT", "")
        if cli_date_format:
            config.option.log_cli_date_format = cli_date_format

    @staticmethod
    def configure_worker_log_path(config: Any, logger: logging.Logger) -> None:
        """Route xdist logs to per-worker files only when env toggle is enabled."""
        enabled = AutomationConfig.get_env_bool("PYTEST_PARALLEL_LOG_TO_FILE")
        if not enabled:
            return

        is_worker = hasattr(config, "workerinput")
        numprocesses = int(getattr(config.option, "numprocesses", 0) or 0)
        if not is_worker and numprocesses <= 0:
            return

        worker_id = "master"
        if hasattr(config, "workerinput"):
            worker_id = str(config.workerinput.get("workerid", "worker"))

        log_dir_value = AutomationConfig.get_env_string(
            "PYTEST_PARALLEL_LOG_PATH", "artifacts/logs/execution"
        )
        log_dir = Path(log_dir_value)
        if not log_dir.is_absolute():
            log_dir = Path(config.rootpath) / log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"pytest-{worker_id}.log"
        effective_level = LogManager.resolve_effective_log_level(config, logger)
        level_no = getattr(logging, effective_level, logging.INFO)

        root_logger = logging.getLogger()
        existing_handler = getattr(config, LogManager.PARALLEL_LOG_HANDLER_ATTR, None)
        if existing_handler is not None:
            root_logger.removeHandler(existing_handler)
            try:
                existing_handler.close()
            finally:
                setattr(config, LogManager.PARALLEL_LOG_HANDLER_ATTR, None)

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
        root_logger.addHandler(file_handler)
        if root_logger.level > level_no:
            root_logger.setLevel(level_no)

        setattr(config, LogManager.PARALLEL_LOG_HANDLER_ATTR, file_handler)
        setattr(config, LogManager.PARALLEL_LOG_PATH_ATTR, log_path)

        role = worker_id if worker_id != "master" else "master"
        logger.info("Parallel logging enabled for %s; writing to %s", role, log_path)

    @staticmethod
    def unconfigure_parallel_file_handler(config: Any) -> None:
        """Remove the per-process file handler when pytest shuts down."""
        handler = getattr(config, LogManager.PARALLEL_LOG_HANDLER_ATTR, None)
        if handler is None:
            return

        root_logger = logging.getLogger()
        root_logger.removeHandler(handler)
        handler.close()
        setattr(config, LogManager.PARALLEL_LOG_HANDLER_ATTR, None)
