# Snapshot Evidence

`robo-automation` owns one browser-evidence subsystem for both action snapshots and failure snapshots. The implementation uses one `SnapshotService` and one `SnapshotWriter`; consuming applications do not implement a second screenshot pipeline.

## Configuration

```ini
CAPTURE_ACTION_SNAPSHOTS=N
CAPTURE_FAILURE_SNAPSHOTS=Y
SNAPSHOT_PATH=${EVIDENCE_PATH}/actions
```

`CAPTURE_ACTION_SNAPSHOTS=Y` captures a `before` and `after` evidence set around every instrumented Playwright action. `CAPTURE_FAILURE_SNAPSHOTS=Y` guarantees failure evidence for failed pytest/setup/teardown flows when that failure is not already represented by a failed action snapshot. Either flag can operate independently.

## Flag behavior

| Action | Failure | Behavior |
| --- | --- | --- |
| N | N | No snapshot evidence |
| N | Y | Failure evidence only |
| Y | N | Before/after evidence for browser actions, including failed actions |
| Y | Y | Action evidence plus failure fallback; matching failures are deduplicated |

A failed action always uses the normal `after` phase with `status=failed`. There is no `after_error` phase.

## Storage

All snapshot evidence uses `SNAPSHOT_PATH` and is separated by artifact type:

```text
${SNAPSHOT_PATH}/
├── screenshots/<process>/...png
├── html/<process>/...html
└── metadata/<process>/...json
```

The matching stem correlates the screenshot, live DOM, and metadata. Unique process/test identifiers separate parallel captures without worker directories. The worker name remains in JSON metadata for diagnostics.

## Action lifecycle

Before metadata contains `capture_type=action`, `phase=before`, and `status=started`. A successful after record contains `phase=after`, `status=passed`, and `duration_ms`. A failed after record contains `phase=after`, `status=failed`, `duration_ms`, `error_type`, and `error`.

Snapshot collection is diagnostic-only. Failure to write a screenshot, DOM, or metadata file is logged and never replaces the real automation exception.

## Failure lifecycle and deduplication

Failure capture is independent of action capture. When action capture is disabled, a failed test can still write PNG, HTML, and JSON evidence. When both flags are enabled, the service records failed-action coverage in process-local correlation state. If the pytest failure matches that action error, the failure policy reuses the action evidence and does not create a duplicate set. An unrelated later failure is not suppressed.

## Runtime activation

The pytest plugin starts the service before browser use. `RoboPage` also performs an idempotent process-local `ensure_snapshot_service()` call so xdist workers and nonstandard fixture paths cannot silently bypass evidence initialization. Both paths share the same singleton service and cannot double-patch Playwright.
