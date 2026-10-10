"""Unified screenshot, DOM, and metadata evidence for browser actions and failures."""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from playwright.sync_api import Locator, Page

from .config import ArtifactPaths, SnapshotConfig
from .correlation import current_correlation

logger = logging.getLogger(__name__)


def _token(value: object, limit: int = 96) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip("-._")
    return (text or "unknown")[:limit]


def _raw_page(value: Any) -> Optional[Page]:
    seen: set[int] = set()
    current = value
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, Page):
            return current
        if isinstance(current, Locator):
            try:
                return current.page
            except Exception:
                return None
        current = getattr(current, "_page", None) or getattr(current, "_robo_page", None)
    return None


@dataclass(frozen=True)
class FailureCoverage:
    process_id: str
    error_type: str
    error_text: str


class SnapshotWriter:
    """Write one correlated PNG/HTML/JSON evidence set."""

    def __init__(self, root: Path, worker_id: str, *, full_page: bool = False) -> None:
        self.root = Path(root)
        self.worker_id = _token(worker_id, 32)
        self.full_page = full_page
        self.screenshot_root = self.root / "screenshots"
        self.html_root = self.root / "html"
        self.metadata_root = self.root / "metadata"

    def ensure_directories(self) -> None:
        self.screenshot_root.mkdir(parents=True, exist_ok=True)
        self.html_root.mkdir(parents=True, exist_ok=True)
        self.metadata_root.mkdir(parents=True, exist_ok=True)

    def capture_metadata(self, *, stem: str, metadata: dict[str, Any]) -> bool:
        """Write metadata when no browser page exists (for example collection failure)."""
        try:
            self.ensure_directories()
            process_id = _token(metadata.get("process_id") or "session", 64)
            metadata_dir = self.metadata_root / process_id
            metadata_dir.mkdir(parents=True, exist_ok=True)
            payload = {"timestamp": time.time(), "worker": self.worker_id, **metadata}
            (metadata_dir / f"{_token(stem, 180)}.json").write_text(
                json.dumps(payload, indent=2, default=str), encoding="utf-8"
            )
            return True
        except Exception as exc:
            logger.warning("Snapshot metadata capture failed (diagnostic only): %s", exc)
            return False

    def capture(self, page: Any, *, stem: str, metadata: dict[str, Any]) -> bool:
        raw = _raw_page(page)
        if raw is None:
            return False
        try:
            if raw.is_closed():
                return False
        except Exception:
            return False
        try:
            self.ensure_directories()
            process_id = _token(metadata.get("process_id") or "session", 64)
            screenshot_dir = self.screenshot_root / process_id
            html_dir = self.html_root / process_id
            metadata_dir = self.metadata_root / process_id
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            html_dir.mkdir(parents=True, exist_ok=True)
            metadata_dir.mkdir(parents=True, exist_ok=True)
            safe_stem = _token(stem, 180)
            raw.screenshot(path=str(screenshot_dir / f"{safe_stem}.png"), full_page=self.full_page)
            (html_dir / f"{safe_stem}.html").write_text(raw.content(), encoding="utf-8")
            payload = {"timestamp": time.time(), "worker": self.worker_id, "url": raw.url, **metadata}
            (metadata_dir / f"{safe_stem}.json").write_text(
                json.dumps(payload, indent=2, default=str), encoding="utf-8"
            )
            return True
        except Exception as exc:
            logger.warning("Snapshot evidence capture failed (diagnostic only): %s", exc)
            return False


class SnapshotService:
    """Independent action and failure capture policies sharing one writer."""

    PAGE_ACTIONS = ("goto", "reload", "go_back", "go_forward", "set_content", "wait_for_load_state", "wait_for_timeout")
    LOCATOR_ACTIONS = ("click", "dblclick", "fill", "clear", "press", "press_sequentially", "type", "check", "uncheck", "set_checked", "select_option", "hover", "focus", "blur", "set_input_files", "drag_to", "scroll_into_view_if_needed", "wait_for")

    def __init__(self, config: SnapshotConfig, paths: ArtifactPaths, *, worker_id: str) -> None:
        self.config = config
        self.writer = SnapshotWriter(paths.action_snapshots, worker_id, full_page=config.full_page)
        self._originals: dict[tuple[type, str], Callable[..., Any]] = {}
        self._sequence = 0
        self._lock = threading.Lock()
        self._coverage: dict[str, FailureCoverage] = {}

    def start(self) -> None:
        print(
            "[SNAPSHOT-RUNTIME-PATH] "
            f"pid={os.getpid()} worker={self.writer.worker_id} "
            f"action={self.config.action_enabled} "
            f"failure={self.config.failure_enabled} "
            f"env_ARTIFACTS_ROOT={os.getenv('ARTIFACTS_ROOT', '<unset>')} "
            f"env_EVIDENCE_PATH={os.getenv('EVIDENCE_PATH', '<unset>')} "
            f"env_SNAPSHOT_PATH={os.getenv('SNAPSHOT_PATH', '<unset>')} "
            f"writer_root={self.writer.root}",
            flush=True,
        )
        if not self.config.enabled:
            return
        self.writer.ensure_directories()
        print(
            "[SNAPSHOT-RUNTIME-PATH] "
            f"directories screenshots={self.writer.screenshot_root} "
            f"html={self.writer.html_root} "
            f"metadata={self.writer.metadata_root}",
            flush=True,
        )
        if self.config.action_enabled:
            for name in self.PAGE_ACTIONS:
                self._patch(Page, name, "page")
            for name in self.LOCATOR_ACTIONS:
                self._patch(Locator, name, "locator")
        logger.info(
            "Snapshot evidence enabled: action=%s failure=%s configured_path=%s resolved_path=%s",
            self.config.action_enabled,
            self.config.failure_enabled,
            os.getenv("SNAPSHOT_PATH", ""),
            self.writer.root,
        )

    def stop(self) -> None:
        for (owner, name), original in self._originals.items():
            setattr(owner, name, original)
        self._originals.clear()

    def _next(self) -> int:
        with self._lock:
            self._sequence += 1
            return self._sequence

    def _patch(self, owner: type, name: str, kind: str) -> None:
        original = getattr(owner, name, None)
        if not callable(original) or (owner, name) in self._originals:
            return
        self._originals[(owner, name)] = original
        service = self

        def wrapped(instance: Any, *args: Any, **kwargs: Any) -> Any:
            page = _raw_page(instance)
            sequence = service._next()
            correlation = current_correlation()
            process_id = str(correlation.get("process_id") or "session")
            target = service._target(kind, instance, args)
            base = f"{sequence:05d}__{_token(name,40)}"
            service.writer.capture(page, stem=f"{base}__before__{_token(process_id,64)}", metadata={
                "capture_type": "action", "phase": "before", "status": "started",
                "sequence": sequence, "action": name, "target": target, **correlation,
            })
            started = time.perf_counter()
            try:
                result = original(instance, *args, **kwargs)
            except Exception as exc:
                duration = (time.perf_counter() - started) * 1000.0
                service.writer.capture(page, stem=f"{base}__after__{_token(process_id,64)}", metadata={
                    "capture_type": "action", "phase": "after", "status": "failed",
                    "sequence": sequence, "action": name, "target": target,
                    "duration_ms": round(duration, 3), "error_type": type(exc).__name__,
                    "error": str(exc), **correlation,
                })
                service._coverage[process_id] = FailureCoverage(process_id, type(exc).__name__, str(exc))
                raise
            duration = (time.perf_counter() - started) * 1000.0
            service.writer.capture(page, stem=f"{base}__after__{_token(process_id,64)}", metadata={
                "capture_type": "action", "phase": "after", "status": "passed",
                "sequence": sequence, "action": name, "target": target,
                "duration_ms": round(duration, 3), **correlation,
            })
            return result

        wrapped.__name__ = getattr(original, "__name__", name)
        wrapped.__doc__ = getattr(original, "__doc__", None)
        setattr(owner, name, wrapped)

    @staticmethod
    def _target(kind: str, instance: Any, args: tuple[Any, ...]) -> str:
        if kind == "page":
            if args and isinstance(args[0], str):
                return args[0][:500]
            return str(getattr(instance, "url", "page"))[:500]
        return str(getattr(instance, "_selector", None) or instance)[:1000]

    def capture_failure(self, page: Any, *, nodeid: str, phase: str, details: str = "", process_id: str = "") -> bool:
        if not self.config.failure_enabled:
            return False
        correlation = current_correlation()
        pid = process_id or str(correlation.get("process_id") or "session")
        covered = self._coverage.get(pid)
        if covered and (
            (covered.error_text and covered.error_text in details)
            or (not covered.error_text and covered.error_type and covered.error_type in details)
        ):
            logger.info("Failure snapshot deduplicated for %s; failed action already captured", nodeid)
            self._coverage.pop(pid, None)
            return False
        stem = f"failure__{_token(nodeid,100)}__{_token(phase,24)}__{_token(pid,64)}"
        metadata = {
            "capture_type": "failure", "phase": phase, "status": "failed",
            "nodeid": nodeid, "details": details, **correlation, "process_id": pid,
        }
        if _raw_page(page) is None:
            return self.writer.capture_metadata(stem=stem, metadata=metadata)
        return self.writer.capture(page, stem=stem, metadata=metadata)


_service_lock = threading.Lock()
_service: Optional[SnapshotService] = None


def ensure_snapshot_service(*, config: SnapshotConfig | None = None, artifact_paths: ArtifactPaths | None = None, rootpath: Path | None = None, worker_id: str | None = None) -> Optional[SnapshotService]:
    global _service
    with _service_lock:
        if _service is not None:
            return _service
        if config is None or artifact_paths is None:
            from .config import RuntimeConfig
            runtime = RuntimeConfig.from_env()
            config = runtime.snapshots
            if not config.enabled:
                return None
            artifact_paths = ArtifactPaths.from_config(rootpath or Path.cwd(), runtime.artifacts)
        elif not config.enabled:
            return None
        _service = SnapshotService(config, artifact_paths, worker_id=worker_id or os.getenv("PYTEST_XDIST_WORKER", "master"))
        _service.start()
        return _service


def stop_snapshot_service() -> None:
    global _service
    with _service_lock:
        service = _service
        _service = None
    if service is not None:
        service.stop()


def capture_failure_snapshot(page: Any, *, nodeid: str, phase: str, details: str = "", process_id: str = "") -> bool:
    service = ensure_snapshot_service()
    if service is None:
        return False
    return service.capture_failure(page, nodeid=nodeid, phase=phase, details=details, process_id=process_id)
