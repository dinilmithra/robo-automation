from pathlib import Path

from robo_automation.config import ArtifactPaths, RuntimeConfig


def test_runtime_config_uses_library_defaults_when_consumer_supplies_nothing(monkeypatch):
    for name in (
        "PYTEST_LOG_LEVEL",
        "PYTEST_PARALLEL_LOG_TO_FILE",
        "TESTCASE_LOG_ENABLED",
        "ENABLE_BROWSER_DIAGNOSTICS",
        "PERF_MONITOR_ENABLED",
        "CAPTURE_ACTION_SNAPSHOTS",
        "WAIT_TIME",
        "ARTIFACTS_ROOT",
    ):
        monkeypatch.delenv(name, raising=False)

    config = RuntimeConfig.from_env()

    assert config.logging.level == "INFO"
    assert config.logging.parallel_file_enabled is False
    assert config.logging.testcase_file_enabled is True
    assert config.diagnostics.enabled is False
    assert config.performance.enabled is True
    assert config.action_snapshots.enabled is False
    assert config.timeouts.wait_time_seconds == 90
    assert config.artifacts.root == "artifacts"


def test_runtime_config_environment_overrides_library_defaults(monkeypatch):
    monkeypatch.setenv("PYTEST_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PYTEST_PARALLEL_LOG_TO_FILE", "Y")
    monkeypatch.setenv("TESTCASE_LOG_ENABLED", "N")
    monkeypatch.setenv("ENABLE_BROWSER_DIAGNOSTICS", "Y")
    monkeypatch.setenv("PERF_MONITOR_ENABLED", "N")
    monkeypatch.setenv("CAPTURE_ACTION_SNAPSHOTS", "Y")
    monkeypatch.setenv("WAIT_TIME", "30")
    monkeypatch.setenv("ARTIFACTS_ROOT", "../runtime-artifacts")

    config = RuntimeConfig.from_env()

    assert config.logging.level == "DEBUG"
    assert config.logging.parallel_file_enabled is True
    assert config.logging.testcase_file_enabled is False
    assert config.diagnostics.enabled is True
    assert config.performance.enabled is False
    assert config.action_snapshots.enabled is True
    assert config.timeouts.wait_time_seconds == 30
    assert config.artifacts.root == "../runtime-artifacts"


def test_artifact_paths_resolve_relative_paths_from_consumer_root(tmp_path):
    config = RuntimeConfig.defaults()

    paths = ArtifactPaths.from_config(tmp_path, config.artifacts)

    assert paths.root == tmp_path / "artifacts"
    assert paths.execution_logs == tmp_path / "artifacts/logs/execution"
    assert paths.testcase_logs == tmp_path / "artifacts/logs/testcases"
    assert paths.performance_logs == tmp_path / "artifacts/logs/performance"
    assert paths.action_snapshots == tmp_path / "artifacts/evidence/actions"


def test_absolute_artifact_override_is_preserved(tmp_path, monkeypatch):
    absolute = tmp_path / "external-artifacts"
    monkeypatch.setenv("ARTIFACTS_ROOT", str(absolute))

    config = RuntimeConfig.from_env()
    paths = ArtifactPaths.from_config(Path("/consumer/project"), config.artifacts)

    assert paths.root == absolute
