"""Collect pytest, Playwright, network, and process performance metrics."""

import heapq
import json
import logging
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import psutil
import pytest
from playwright.sync_api import Locator, Page

from .correlation import current_correlation
from .config import ArtifactPaths, PerformanceConfig, RuntimeConfig

logger = logging.getLogger(__name__)


class PytestPerformanceMonitor:
    """Collect unified pytest, Playwright, network, and resource timings.

    ``PERF_MONITOR_ENABLED`` is the master switch. ``PERF_MONITOR_ACTIONS``
    controls Playwright action instrumentation and ``PERF_MONITOR_FRAMEWORK``
    controls pytest/framework lifecycle timing. Both use the same threshold,
    slow classification, JSONL stream, and summary output.
    """

    _PAGE_ACTIONS: Tuple[str, ...] = (
        "goto",
        "reload",
        "go_back",
        "go_forward",
        "set_content",
        "wait_for_load_state",
        "wait_for_timeout",
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
        "wait_for",
    )

    def __init__(
        self,
        config: pytest.Config,
        performance_config: Optional[PerformanceConfig] = None,
        artifact_paths: Optional[ArtifactPaths] = None,
    ) -> None:
        """Initialize worker-specific outputs, thresholds, and monitor state.

        ``performance_config`` and ``artifact_paths`` are normally supplied by
        robo-automation fixtures. Optional fallbacks preserve the standalone
        constructor for existing consumers.
        """
        if performance_config is None or artifact_paths is None:
            runtime = RuntimeConfig.from_env()
            performance_config = performance_config or runtime.performance
            artifact_paths = artifact_paths or ArtifactPaths.from_config(
                Path(config.rootpath), runtime.artifacts
            )

        self.worker_id = str(
            getattr(config, "workerinput", {}).get("workerid", "master")
        )
        path = artifact_paths.performance_logs
        try:
            path.relative_to(artifact_paths.root)
        except ValueError:
            path = path / performance_config.run_id

        path.mkdir(parents=True, exist_ok=True)
        self.output = path / f"{self.worker_id}.jsonl"
        self.summary_output = path / f"{self.worker_id}-summary.json"
        self.process = psutil.Process(os.getpid())
        self.sample_interval = performance_config.sample_interval
        self.include_descendants = self.worker_id == "master"
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._sample_resources,
            daemon=True,
        )
        self.stream = self.output.open("a", encoding="utf-8")
        self.flush_every = performance_config.flush_every
        self._pending_writes = 0

        self.actions_enabled = performance_config.actions_enabled
        self.framework_enabled = performance_config.framework_enabled
        self.console_enabled = performance_config.console_enabled
        self.threshold_ms = performance_config.threshold_ms
        self.slow_ms = performance_config.slow_ms
        self.summary_limit = performance_config.summary_limit

        self._original_methods: Dict[Tuple[type, str], Callable[..., Any]] = {}

        # Keep bounded timing state. A long parallel suite can execute tens of
        # thousands of Playwright actions; retaining every record per worker
        # wastes memory when the report only needs aggregate metrics and the
        # slowest N operations.
        self._timing_count = 0
        self._slow_count = 0
        self._heap_sequence = 0
        self._slowest_heap: List[Tuple[float, int, Dict[str, Any]]] = []
        self._timing_stats: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(
            lambda: {
                "count": 0.0,
                "total_ms": 0.0,
                "max_ms": 0.0,
                "failures": 0.0,
            }
        )

    def write(self, record: Dict[str, Any]) -> None:
        """Append a timestamped worker record to the JSONL event stream."""
        record.setdefault("timestamp", time.time())
        record.setdefault("worker", self.worker_id)
        for key, value in current_correlation().items():
            record.setdefault(key, value)
        with self.lock:
            self.stream.write(json.dumps(record, default=str) + "\n")
            self._pending_writes += 1
            if self._pending_writes >= self.flush_every:
                self.stream.flush()
                self._pending_writes = 0

    def start(self) -> None:
        """Start resource sampling and optional Playwright instrumentation."""
        self.write(
            {
                "type": "pytest_monitor_start",
                "pid": os.getpid(),
                "actions_enabled": self.actions_enabled,
                "framework_enabled": self.framework_enabled,
            }
        )
        if self.actions_enabled:
            self._patch_playwright_actions()
        self.thread.start()

    def stop(self) -> None:
        """Stop monitoring, restore patched methods, and finalize outputs."""
        self.stop_event.set()
        self.thread.join(timeout=2)
        self._restore_playwright_actions()
        self._write_summary()
        self.write({"type": "pytest_monitor_end", "pid": os.getpid()})
        with self.lock:
            self.stream.flush()
            self._pending_writes = 0
            self.stream.close()

    def _sample_resources(self) -> None:
        """Sample host and monitored process-tree resource usage until stopped."""
        self.process.cpu_percent(None)
        while not self.stop_event.is_set():
            virtual = psutil.virtual_memory()
            processes = [self.process]
            if self.include_descendants:
                processes += self.process.children(recursive=True)
            cpu_total = 0.0
            memory_total = 0
            running_count = 0
            for process in processes:
                try:
                    if not process.is_running():
                        continue
                    cpu_total += process.cpu_percent(None)
                    memory_total += process.memory_info().rss
                    running_count += 1
                except (
                    psutil.AccessDenied,
                    psutil.NoSuchProcess,
                    psutil.ZombieProcess,
                ):
                    continue
            self.write(
                {
                    "type": "resource",
                    "host_cpu_percent": psutil.cpu_percent(None),
                    "host_memory_percent": virtual.percent,
                    "host_memory_available_mb": round(
                        virtual.available / 1024**2,
                        1,
                    ),
                    "process_tree_cpu_percent": round(cpu_total, 2),
                    "process_tree_memory_mb": round(
                        memory_total / 1024**2,
                        1,
                    ),
                    "process_tree_count": running_count,
                }
            )
            self.stop_event.wait(self.sample_interval)

    def attach_page(self, page: Page) -> None:
        """Attach request-to-response timing callbacks to a Playwright page."""
        request_starts: Dict[int, float] = {}

        def on_request(request: Any) -> None:
            """Record the start time for an outgoing browser request."""
            request_starts[id(request)] = time.perf_counter()

        def on_response(response: Any) -> None:
            """Write elapsed network timing for a matched browser response."""
            started = request_starts.pop(id(response.request), None)
            if started is not None:
                self.write(
                    {
                        "type": "response",
                        "url": response.url,
                        "status": response.status,
                        "resource_type": response.request.resource_type,
                        "request_to_response_ms": round(
                            (time.perf_counter() - started) * 1000,
                            2,
                        ),
                    }
                )

        page.on("request", on_request)
        page.on("response", on_response)

    def _patch_playwright_actions(self) -> None:
        """Instrument commonly used synchronous Playwright actions.

        Patching occurs only when PERF_MONITOR_ACTIONS is true. This keeps
        the disabled path effectively free of per-action profiling overhead.
        """
        for method_name in self._PAGE_ACTIONS:
            self._patch_method(Page, method_name, target_kind="page")

        for method_name in self._LOCATOR_ACTIONS:
            self._patch_method(Locator, method_name, target_kind="locator")

    def _patch_method(
        self,
        owner: type,
        method_name: str,
        *,
        target_kind: str,
    ) -> None:
        """Wrap one Playwright method with monitor timing instrumentation."""
        original = getattr(owner, method_name, None)
        if original is None or not callable(original):
            return

        key = (owner, method_name)
        if key in self._original_methods:
            return

        self._original_methods[key] = original
        monitor = self

        def timed(instance: Any, *args: Any, **kwargs: Any) -> Any:
            """Invoke the original Playwright method through the timing recorder."""
            target = monitor._describe_target(
                target_kind,
                instance,
                args,
                kwargs,
            )
            return monitor._time_action(
                method_name,
                target,
                lambda: original(instance, *args, **kwargs),
                instance if isinstance(instance, Page) else None,
            )

        setattr(owner, method_name, timed)

    def _restore_playwright_actions(self) -> None:
        """Restore all Playwright methods replaced by this monitor."""
        for (owner, method_name), original in self._original_methods.items():
            setattr(owner, method_name, original)
        self._original_methods.clear()

    @staticmethod
    def _describe_target(
        target_kind: str,
        instance: Any,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> str:
        """Describe the page URL or locator targeted by an action."""
        if target_kind == "page":
            if args:
                value = args[0]
                if isinstance(value, str):
                    return value[:500]
            url = kwargs.get("url")
            if url:
                return str(url)[:500]
            try:
                return str(instance.url)[:500]
            except Exception:
                return "page"

        selector = getattr(instance, "_selector", None)
        if selector:
            return str(selector)[:1000]

        return str(instance)[:1000]

    def _time_action(
        self,
        action: str,
        target: str,
        operation: Callable[[], Any],
        page: Optional[Page],
    ) -> Any:
        """Execute an action and record its duration and outcome."""
        started = time.perf_counter()
        ok = False
        error_type: Optional[str] = None

        try:
            result = operation()
            ok = True
            return result
        except Exception as exc:
            error_type = type(exc).__name__
            raise
        finally:
            duration_ms = round(
                (time.perf_counter() - started) * 1000,
                2,
            )
            self._record_timing(
                event_type="playwright_action",
                action=action,
                target=target,
                duration_ms=duration_ms,
                ok=ok,
                error_type=error_type,
                final_url=(page.url if page is not None else None),
            )

    def _record_timing(
        self,
        *,
        event_type: str,
        action: str,
        duration_ms: float,
        ok: bool,
        target: str = "",
        error_type: Optional[str] = None,
        final_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Aggregate a timing and emit qualifying event and console records."""
        key = (event_type, action)
        stats = self._timing_stats[key]
        stats["count"] += 1
        stats["total_ms"] += duration_ms
        stats["max_ms"] = max(stats["max_ms"], duration_ms)
        if not ok:
            stats["failures"] += 1

        record: Dict[str, Any] = {
            "type": event_type,
            "action": action,
            "ok": ok,
            "duration_ms": duration_ms,
            "slow": duration_ms >= self.slow_ms,
        }
        if target:
            record["target"] = target
        if final_url:
            record["final_url"] = final_url
        if error_type:
            record["error_type"] = error_type
        if metadata:
            record.update(metadata)

        self._timing_count += 1
        if record["slow"]:
            self._slow_count += 1

        # Retain only the N slowest records in memory. The full qualifying
        # event stream remains available in JSONL on disk.
        self._heap_sequence += 1
        heap_item = (duration_ms, self._heap_sequence, record)
        if len(self._slowest_heap) < self.summary_limit:
            heapq.heappush(self._slowest_heap, heap_item)
        elif duration_ms > self._slowest_heap[0][0]:
            heapq.heapreplace(self._slowest_heap, heap_item)

        if duration_ms >= self.threshold_ms or not ok:
            self.write(record)

        if self.console_enabled and (duration_ms >= self.threshold_ms or not ok):
            level = logging.WARNING if record["slow"] or not ok else logging.INFO
            logger.log(
                level,
                "PERF worker=%s type=%s action=%s duration=%.2fms ok=%s target=%s",
                self.worker_id,
                event_type,
                action,
                duration_ms,
                ok,
                target,
            )

    def record_framework_duration(
        self,
        action: str,
        duration_ms: float,
        *,
        ok: bool = True,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a framework/conftest duration measured outside ``measure``."""
        if not self.framework_enabled:
            return
        self._record_timing(
            event_type="framework_action",
            action=action,
            duration_ms=round(duration_ms, 2),
            ok=ok,
            error_type=error_type,
            metadata=metadata,
        )

    @contextmanager
    def measure(
        self,
        action: str,
        *,
        event_type: str = "framework_action",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Iterator[None]:
        """Time a framework operation and write it to the unified monitor."""
        if event_type == "framework_action" and not self.framework_enabled:
            yield
            return

        started = time.perf_counter()
        ok = False
        error_type: Optional[str] = None
        try:
            yield
            ok = True
        except Exception as exc:
            error_type = type(exc).__name__
            raise
        finally:
            self._record_timing(
                event_type=event_type,
                action=action,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                ok=ok,
                error_type=error_type,
                metadata=metadata,
            )

    def _write_summary(self) -> None:
        """Write aggregated operation statistics and slowest timings atomically."""
        by_operation = []
        for (event_type, action), values in self._timing_stats.items():
            count = int(values["count"])
            total_ms = round(values["total_ms"], 2)
            by_operation.append(
                {
                    "type": event_type,
                    "action": action,
                    "count": count,
                    "total_ms": total_ms,
                    "average_ms": round(total_ms / count, 2) if count else 0.0,
                    "max_ms": round(values["max_ms"], 2),
                    "failures": int(values["failures"]),
                }
            )

        by_operation.sort(key=lambda item: item["total_ms"], reverse=True)
        slowest = [
            item[2]
            for item in sorted(
                self._slowest_heap,
                key=lambda item: item[0],
                reverse=True,
            )
        ]

        summary = {
            "worker": self.worker_id,
            "generated_at": time.time(),
            "timing_count": self._timing_count,
            "slow_count": self._slow_count,
            "threshold_ms": self.threshold_ms,
            "slow_threshold_ms": self.slow_ms,
            "summary_limit": self.summary_limit,
            "by_operation": by_operation,
            "slowest_operations": slowest,
        }

        temp_path = self.summary_output.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(summary, indent=2, default=str),
            encoding="utf-8",
        )
        temp_path.replace(self.summary_output)

    @staticmethod
    def merge_worker_summaries(
        performance_path: Path, summary_limit: int = 50
    ) -> Optional[Path]:
        """Create one run-level summary from master/xdist worker summaries.

        Raw JSONL remains worker-specific for efficient append-only logging.
        The merged JSON is intended for human/CI bottleneck analysis.
        """
        summary_files = sorted(performance_path.glob("*-summary.json"))
        summary_files = [
            path for path in summary_files if path.name != "performance-summary.json"
        ]
        if not summary_files:
            return None

        operation_totals: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(
            lambda: {
                "count": 0.0,
                "total_ms": 0.0,
                "max_ms": 0.0,
                "failures": 0.0,
            }
        )
        slowest_candidates: List[Dict[str, Any]] = []
        timing_count = 0
        slow_count = 0
        slow_threshold_ms = 0.0
        threshold_ms = 0.0
        workers: List[str] = []
        resolved_summary_limit = max(0, int(summary_limit))

        for summary_file in summary_files:
            try:
                data = json.loads(summary_file.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue

            workers.append(str(data.get("worker", summary_file.stem)))
            resolved_summary_limit = max(
                resolved_summary_limit, int(data.get("summary_limit", 0) or 0)
            )
            timing_count += int(data.get("timing_count", 0) or 0)
            slow_count += int(data.get("slow_count", 0) or 0)
            threshold_ms = max(threshold_ms, float(data.get("threshold_ms", 0) or 0))
            slow_threshold_ms = max(
                slow_threshold_ms,
                float(data.get("slow_threshold_ms", 0) or 0),
            )

            for item in data.get("by_operation", []):
                key = (str(item.get("type", "")), str(item.get("action", "")))
                values = operation_totals[key]
                values["count"] += float(item.get("count", 0) or 0)
                values["total_ms"] += float(item.get("total_ms", 0) or 0)
                values["max_ms"] = max(
                    values["max_ms"], float(item.get("max_ms", 0) or 0)
                )
                values["failures"] += float(item.get("failures", 0) or 0)

            for item in data.get("slowest_operations", []):
                if isinstance(item, dict):
                    candidate = dict(item)
                    candidate.setdefault("worker", data.get("worker", "unknown"))
                    slowest_candidates.append(candidate)

        by_operation: List[Dict[str, Any]] = []
        for (event_type, action), values in operation_totals.items():
            count = int(values["count"])
            total_ms = round(values["total_ms"], 2)
            by_operation.append(
                {
                    "type": event_type,
                    "action": action,
                    "count": count,
                    "total_ms": total_ms,
                    "average_ms": round(total_ms / count, 2) if count else 0.0,
                    "max_ms": round(values["max_ms"], 2),
                    "failures": int(values["failures"]),
                }
            )
        by_operation.sort(key=lambda item: item["total_ms"], reverse=True)

        slowest_candidates.sort(
            key=lambda item: float(item.get("duration_ms", 0) or 0),
            reverse=True,
        )
        limit = resolved_summary_limit
        merged = {
            "generated_at": time.time(),
            "workers": sorted(set(workers)),
            "timing_count": timing_count,
            "slow_count": slow_count,
            "threshold_ms": threshold_ms,
            "slow_threshold_ms": slow_threshold_ms,
            "by_operation": by_operation,
            "slowest_operations": slowest_candidates[:limit],
        }

        output = performance_path / "performance-summary.json"
        temp_path = output.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(merged, indent=2, default=str),
            encoding="utf-8",
        )
        temp_path.replace(output)
        return output
