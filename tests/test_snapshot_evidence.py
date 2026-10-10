import json
from pathlib import Path

import pytest

from robo_automation.config import ArtifactConfig, ArtifactPaths, SnapshotConfig
from robo_automation.snapshot_evidence import SnapshotService, SnapshotWriter


class FakePage:
    def __init__(self):
        self.url = "https://example.test"
        self.shots = []
    def is_closed(self): return False
    def screenshot(self, *, path, full_page=False):
        Path(path).write_bytes(b"png")
        self.shots.append(path)
    def content(self): return "<html>ok</html>"


def paths(tmp_path):
    return ArtifactPaths.from_config(tmp_path, ArtifactConfig())


@pytest.mark.parametrize(
    "action,failure,enabled",
    [(False, False, False), (False, True, True), (True, False, True), (True, True, True)],
)
def test_flag_matrix(action, failure, enabled):
    cfg = SnapshotConfig(action_enabled=action, failure_enabled=failure)
    assert cfg.enabled is enabled


@pytest.mark.parametrize("worker_id", ["gw0", "gw9"])
def test_writer_separates_artifact_types(tmp_path, monkeypatch, worker_id):
    import robo_automation.snapshot_evidence as module
    monkeypatch.setattr(module, "_raw_page", lambda value: value)
    writer = SnapshotWriter(tmp_path / "evidence", worker_id)
    page = FakePage()
    process_id = "PR-F73592C8C236-A1-E169D89E"
    assert writer.capture(page, stem="one", metadata={"process_id": process_id})
    for artifact_type, extension in (("screenshots", "png"), ("html", "html"), ("metadata", "json")):
        artifact_root = tmp_path / "evidence" / artifact_type
        assert (artifact_root / process_id / f"one.{extension}").is_file()
        assert not (artifact_root / worker_id).exists()
    payload = json.loads((writer.metadata_root / process_id / "one.json").read_text())
    assert payload["worker"] == worker_id


def test_failure_only_capture_works_without_action_capture(tmp_path, monkeypatch):
    import robo_automation.snapshot_evidence as module
    monkeypatch.setattr(module, "_raw_page", lambda value: value)
    service = SnapshotService(SnapshotConfig(failure_enabled=True), paths(tmp_path), worker_id="gw1")
    service.start()
    assert service.capture_failure(FakePage(), nodeid="test_x", phase="call", details="boom", process_id="p2")
    metadata = list((tmp_path / "artifacts/evidence/actions/metadata/p2").glob("*.json"))
    assert len(metadata) == 1
    assert json.loads(metadata[0].read_text())["capture_type"] == "failure"


@pytest.mark.parametrize("source_closed", [False, True])
def test_failure_capture_resolves_open_page_in_same_context(tmp_path, monkeypatch, source_closed):
    from types import SimpleNamespace
    import robo_automation.snapshot_evidence as module

    monkeypatch.setattr(module, "_raw_page", lambda value: value)
    source = FakePage()
    source.is_closed = lambda: source_closed
    older_page = FakePage()
    destination = FakePage()
    destination.url = "https://example.test/user-hub"
    closed_page = FakePage()
    closed_page.is_closed = lambda: True
    source.context = SimpleNamespace(pages=[older_page, destination, closed_page])
    service = SnapshotService(SnapshotConfig(failure_enabled=True), paths(tmp_path), worker_id="gw1")

    assert service.capture_failure(source, nodeid="test_popup", phase="call", process_id="popup")

    captured = destination if source_closed else source
    assert len(captured.shots) == 1
    assert not older_page.shots
    assert not closed_page.shots
    assert not (source if source_closed else destination).shots
    assert len(list((service.writer.html_root / "popup").glob("*.html"))) == 1
    metadata = list((service.writer.metadata_root / "popup").glob("*.json"))
    assert len(metadata) == 1
    assert json.loads(metadata[0].read_text())["url"] == captured.url


@pytest.mark.parametrize("context_available", [False, True])
def test_failure_capture_without_open_context_page_saves_metadata(tmp_path, monkeypatch, context_available):
    from types import SimpleNamespace
    import robo_automation.snapshot_evidence as module

    monkeypatch.setattr(module, "_raw_page", lambda value: value)
    source = FakePage()
    source.is_closed = lambda: True
    if context_available:
        source.context = SimpleNamespace(pages=[])
    service = SnapshotService(SnapshotConfig(failure_enabled=True), paths(tmp_path), worker_id="gw1")

    assert service.capture_failure(source, nodeid="test_closed", phase="teardown", process_id="closed")

    assert not source.shots
    metadata = list((service.writer.metadata_root / "closed").glob("*.json"))
    assert len(metadata) == 1
    assert json.loads(metadata[0].read_text())["snapshot_reason"]


def test_action_failure_deduplicates_matching_test_failure(tmp_path, monkeypatch):
    import robo_automation.snapshot_evidence as module
    monkeypatch.setattr(module, "_raw_page", lambda value: value)
    service = SnapshotService(SnapshotConfig(action_enabled=True, failure_enabled=True), paths(tmp_path), worker_id="gw2")
    service._coverage["p3"] = module.FailureCoverage("p3", "ValueError", "bad value")
    assert not service.capture_failure(FakePage(), nodeid="test_x", phase="call", details="ValueError: bad value", process_id="p3")


def test_unrelated_failure_is_not_deduplicated(tmp_path, monkeypatch):
    import robo_automation.snapshot_evidence as module
    monkeypatch.setattr(module, "_raw_page", lambda value: value)
    service = SnapshotService(SnapshotConfig(action_enabled=True, failure_enabled=True), paths(tmp_path), worker_id="gw3")
    service._coverage["p4"] = module.FailureCoverage("p4", "TimeoutError", "old action")
    assert service.capture_failure(FakePage(), nodeid="test_x", phase="call", details="AssertionError: later failure", process_id="p4")

def test_action_capture_writes_before_and_after(tmp_path, monkeypatch):
    import robo_automation.snapshot_evidence as module
    monkeypatch.setattr(module, "_raw_page", lambda value: value)
    monkeypatch.setattr(module, "current_correlation", lambda: {"process_id": "p5", "test_case_id": "t5"})
    class ActionPage(FakePage):
        def click(self): return "ok"
    service = SnapshotService(SnapshotConfig(action_enabled=True), paths(tmp_path), worker_id="gw4")
    service._patch(ActionPage, "click", "locator")
    try:
        assert ActionPage().click() == "ok"
    finally:
        service.stop()
    files = list((tmp_path / "artifacts/evidence/actions/metadata/p5").glob("*.json"))
    payloads = [json.loads(p.read_text()) for p in files]
    assert {(p["phase"], p["status"]) for p in payloads} == {("before", "started"), ("after", "passed")}


def test_failed_action_uses_after_failed_and_never_masks_error(tmp_path, monkeypatch):
    import robo_automation.snapshot_evidence as module
    monkeypatch.setattr(module, "_raw_page", lambda value: value)
    monkeypatch.setattr(module, "current_correlation", lambda: {"process_id": "p6"})
    class ActionPage(FakePage):
        def click(self): raise RuntimeError("real failure")
    service = SnapshotService(SnapshotConfig(action_enabled=True, failure_enabled=True), paths(tmp_path), worker_id="gw5")
    service._patch(ActionPage, "click", "locator")
    try:
        with pytest.raises(RuntimeError, match="real failure"):
            ActionPage().click()
    finally:
        service.stop()
    files = list((tmp_path / "artifacts/evidence/actions/metadata/p6").glob("*.json"))
    payloads = [json.loads(p.read_text()) for p in files]
    failed = [p for p in payloads if p["phase"] == "after"]
    assert len(failed) == 1 and failed[0]["status"] == "failed"
    assert failed[0]["error_type"] == "RuntimeError"

def test_failure_without_page_writes_metadata_only(tmp_path):
    service = SnapshotService(SnapshotConfig(failure_enabled=True), paths(tmp_path), worker_id="gw6")
    service.start()
    assert service.capture_failure(None, nodeid="collection", phase="collection", details="import failed", process_id="p7")
    assert list((tmp_path / "artifacts/evidence/actions/metadata/p7").glob("*.json"))
    assert not (tmp_path / "artifacts/evidence/actions/metadata/gw6").exists()
    assert not list((tmp_path / "artifacts/evidence/actions/screenshots/p7").glob("*.png"))
