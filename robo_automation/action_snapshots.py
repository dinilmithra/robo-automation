"""Optional before/after evidence capture for Playwright user actions."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from playwright.sync_api import Locator, Page

from .config import ActionSnapshotConfig, ArtifactPaths
from .correlation import current_correlation

logger = logging.getLogger(__name__)


def _safe_token(value: object, limit: int = 80) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip("-._")
    return (token or "unknown")[:limit]


class ActionSnapshotMonitor:
    """Capture screenshot + live DOM before and after Playwright UI actions.

    The monitor is deliberately independent from performance monitoring.  It is
    enabled only when ``CAPTURE_ACTION_SNAPSHOTS`` resolves to true.  Capture
    failures are diagnostic-only and never mask the browser action itself.
    """

    _PAGE_ACTIONS: Tuple[str, ...] = (
        "goto",
        "reload",
        "go_back",
        "go_forward",
        "set_content",
    )

    _LOCATOR_ACTIONS: Tuple[str, ...] = (
        "click",
        "dblclick",
        "fill",
        "clear",
        "press",
        "press_sequentially",
        "type",
        "check",
        "uncheck",
        "set_checked",
        "select_option",
        "hover",
        "focus",
        "blur",
        "set_input_files",
        "drag_to",
        "scroll_into_view_if_needed",
    )

    def __init__(
        self,
        config: ActionSnapshotConfig,
        artifact_paths: ArtifactPaths,
        *,
        worker_id: str = "master",
    ) -> None:
        self.config = config
        self.worker_id = _safe_token(worker_id, 32)
        self.root = artifact_paths.action_snapshots / self.worker_id
        self._original_methods: Dict[Tuple[type, str], Callable[..., Any]] = {}
        self._lock = threading.Lock()
        self._sequence = 0

    def start(self) -> None:
        if not self.config.enabled:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        for name in self._PAGE_ACTIONS:
            self._patch_method(Page, name, "page")
        for name in self._LOCATOR_ACTIONS:
            self._patch_method(Locator, name, "locator")
        logger.info("Action snapshots enabled at %s", self.root)

    def stop(self) -> None:
        for (owner, method_name), original in self._original_methods.items():
            setattr(owner, method_name, original)
        self._original_methods.clear()

    def _patch_method(self, owner: type, method_name: str, target_kind: str) -> None:
        original = getattr(owner, method_name, None)
        if original is None or not callable(original):
            return
        key = (owner, method_name)
        if key in self._original_methods:
            return
        self._original_methods[key] = original
        monitor = self

        def observed(instance: Any, *args: Any, **kwargs: Any) -> Any:
            page = monitor._resolve_page(instance)
            sequence = monitor._next_sequence()
            target = monitor._describe_target(target_kind, instance, args, kwargs)
            monitor._capture(
                page,
                sequence,
                method_name,
                "before",
                target=target,
                status="started",
            )
            started = time.perf_counter()
            try:
                result = original(instance, *args, **kwargs)
            except Exception as exc:
                monitor._capture(
                    page,
                    sequence,
                    method_name,
                    "after",
                    target=target,
                    status="failed",
                    duration_ms=(time.perf_counter() - started) * 1000.0,
                    error=exc,
                )
                raise
            monitor._capture(
                page,
                sequence,
                method_name,
                "after",
                target=target,
                status="passed",
                duration_ms=(time.perf_counter() - started) * 1000.0,
            )
            return result

        observed.__name__ = getattr(original, "__name__", method_name)
        observed.__doc__ = getattr(original, "__doc__", None)
        setattr(owner, method_name, observed)

    def _next_sequence(self) -> int:
        with self._lock:
            self._sequence += 1
            return self._sequence

    @staticmethod
    def _resolve_page(instance: Any) -> Optional[Page]:
        if isinstance(instance, Page):
            return instance
        if isinstance(instance, Locator):
            try:
                return instance.page
            except Exception:
                return None
        return None

    @staticmethod
    def _describe_target(
        target_kind: str,
        instance: Any,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> str:
        if target_kind == "page":
            if args and isinstance(args[0], str):
                return args[0][:500]
            try:
                return str(instance.url)[:500]
            except Exception:
                return "page"
        selector = getattr(instance, "_selector", None)
        if selector:
            return str(selector)[:1000]
        return str(instance)[:1000]

    def _capture(
        self,
        page: Optional[Page],
        sequence: int,
        action: str,
        phase: str,
        *,
        target: str,
        status: str,
        duration_ms: float | None = None,
        error: Exception | None = None,
    ) -> None:
        if page is None or not self.config.enabled:
            return
        try:
            if page.is_closed():
                return
        except Exception:
            return

        correlation = current_correlation()
        process_id = _safe_token(correlation.get("process_id") or "session", 64)
        stem = (
            f"{sequence:05d}__{_safe_token(action, 40)}__{_safe_token(phase, 24)}"
            f"__{process_id}"
        )
        directory = self.root / process_id
        try:
            directory.mkdir(parents=True, exist_ok=True)
            screenshot_path = directory / f"{stem}.png"
            html_path = directory / f"{stem}.html"
            metadata_path = directory / f"{stem}.json"

            page.screenshot(path=str(screenshot_path), full_page=self.config.full_page)
            if self.config.capture_html:
                html_path.write_text(page.content(), encoding="utf-8")

            payload = {
                "timestamp": time.time(),
                "worker": self.worker_id,
                "sequence": sequence,
                "action": action,
                "phase": phase,
                "status": status,
                "target": target,
                "url": page.url,
                **correlation,
            }
            if duration_ms is not None:
                payload["duration_ms"] = round(duration_ms, 3)
            if error is not None:
                payload["error_type"] = type(error).__name__
                payload["error"] = str(error)
            metadata_path.write_text(
                json.dumps(payload, indent=2, default=str), encoding="utf-8"
            )
        except Exception as exc:  # diagnostic evidence must never break the test action
            logger.debug(
                "Unable to capture %s action snapshot for %s: %s",
                phase,
                action,
                exc,
            )
