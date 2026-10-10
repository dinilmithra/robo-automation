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


def test_action_snapshot_monitor_uses_after_phase_for_failed_action(
    monkeypatch, tmp_path
):
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


def test_action_snapshot_monitor_covers_wait_actions():
    assert "wait_for_load_state" in ActionSnapshotMonitor._PAGE_ACTIONS
    assert "wait_for_timeout" in ActionSnapshotMonitor._PAGE_ACTIONS
    assert "wait_for" in ActionSnapshotMonitor._LOCATOR_ACTIONS


def test_action_snapshot_monitor_separates_artifact_types(tmp_path):
    class FakePage:
        url = "https://example.test"

        def is_closed(self):
            return False

        def screenshot(self, *, path, full_page):
            del full_page
            Path(path).write_bytes(b"png")

        def content(self):
            return "<html><body>snapshot</body></html>"

    monitor = ActionSnapshotMonitor(
        ActionSnapshotConfig(enabled=True, capture_html=True),
        _paths(tmp_path),
        worker_id="gw2",
    )
    monitor._capture(
        FakePage(),
        1,
        "click",
        "before",
        target="button",
        status="started",
    )

    root = _paths(tmp_path).action_snapshots
    assert len(list((root / "screenshots" / "gw2").rglob("*.png"))) == 1
    assert len(list((root / "html" / "gw2").rglob("*.html"))) == 1
    assert len(list((root / "metadata" / "gw2").rglob("*.json"))) == 1


def test_runtime_monitor_lazy_start_creates_evidence_directories(monkeypatch, tmp_path):
    from robo_automation import action_snapshots as snapshots
    from robo_automation.config import ArtifactPaths

    snapshots.stop_action_snapshot_monitor()
    monkeypatch.setenv("CAPTURE_ACTION_SNAPSHOTS", "Y")
    monkeypatch.setenv("SNAPSHOT_PATH", str(tmp_path / "evidence" / "actions"))

    monitor = snapshots.ensure_action_snapshot_monitor(rootpath=tmp_path, worker_id="gw7")
    try:
        assert monitor is not None
        assert (tmp_path / "evidence" / "actions" / "screenshots" / "gw7").is_dir()
        assert (tmp_path / "evidence" / "actions" / "html" / "gw7").is_dir()
        assert (tmp_path / "evidence" / "actions" / "metadata" / "gw7").is_dir()
        assert snapshots.ensure_action_snapshot_monitor(rootpath=tmp_path) is monitor
    finally:
        snapshots.stop_action_snapshot_monitor()
