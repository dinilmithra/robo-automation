from pathlib import Path

import pytest
from playwright.sync_api import Page

from robo_automation.action_snapshots import ActionSnapshotMonitor
from robo_automation.config import ActionSnapshotConfig, ArtifactConfig, ArtifactPaths


def _paths(tmp_path: Path) -> ArtifactPaths:
    return ArtifactPaths.from_config(tmp_path, ArtifactConfig())


def test_action_snapshot_monitor_captures_before_and_after(monkeypatch, tmp_path):
    calls = []

    def fake_goto(instance, url, **kwargs):
        del instance, kwargs
        return f"loaded:{url}"

    monkeypatch.setattr(Page, "goto", fake_goto)
    monitor = ActionSnapshotMonitor(
        ActionSnapshotConfig(enabled=True), _paths(tmp_path), worker_id="gw0"
    )
    monkeypatch.setattr(
        monitor,
        "_capture",
        lambda page, sequence, action, phase, **kwargs: calls.append(
            (sequence, action, phase, kwargs.get("target"), kwargs.get("status"))
        ),
    )

    page = object.__new__(Page)
    monitor.start()
    try:
        assert page.goto("https://example.test") == "loaded:https://example.test"
    finally:
        monitor.stop()

    assert [call[2] for call in calls] == ["before", "after"]
    assert calls[0][1] == "goto"
    assert calls[0][3] == "https://example.test"
    assert calls[0][4] == "started"
    assert calls[1][4] == "passed"


def test_action_snapshot_monitor_uses_after_phase_for_failed_action(monkeypatch, tmp_path):
    calls = []

    def fake_goto(instance, url, **kwargs):
        del instance, url, kwargs
        raise RuntimeError("boom")

    monkeypatch.setattr(Page, "goto", fake_goto)
    monitor = ActionSnapshotMonitor(
        ActionSnapshotConfig(enabled=True), _paths(tmp_path), worker_id="gw1"
    )
    monkeypatch.setattr(
        monitor,
        "_capture",
        lambda page, sequence, action, phase, **kwargs: calls.append(
            (phase, kwargs.get("status"), kwargs.get("error"))
        ),
    )

    page = object.__new__(Page)
    monitor.start()
    try:
        with pytest.raises(RuntimeError, match="boom"):
            page.goto("https://example.test")
    finally:
        monitor.stop()

    assert calls[0][:2] == ("before", "started")
    assert calls[1][0:2] == ("after", "failed")
    assert isinstance(calls[1][2], RuntimeError)
