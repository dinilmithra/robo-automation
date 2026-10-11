# Action and Failure Snapshots

Snapshots provide visual evidence of what happened while an automation test was running. They are useful when reviewing test results or investigating a failure.

Configure snapshot capture using:

```text
CAPTURE_ACTION_SNAPSHOTS=N
CAPTURE_FAILURE_SNAPSHOTS=Y
SNAPSHOT_FULL_PAGE=N
SNAPSHOT_PATH=${ARTIFACTS_ROOT}/snapshots
```

| Setting | Purpose |
| --- | --- |
| `CAPTURE_ACTION_SNAPSHOTS` | Capture screenshots before and after supported automation actions. |
| `CAPTURE_FAILURE_SNAPSHOTS` | Capture screenshot evidence when a test fails. |
| `SNAPSHOT_FULL_PAGE` | Capture the full page instead of only the visible area. |
| `SNAPSHOT_PATH` | Folder where snapshot evidence is stored. The standard project setting is `${ARTIFACTS_ROOT}/snapshots`. |

## Recommended configuration

For normal automation execution, failure snapshots provide useful evidence without capturing screenshots for every action:

```text
CAPTURE_ACTION_SNAPSHOTS=N
CAPTURE_FAILURE_SNAPSHOTS=Y
SNAPSHOT_FULL_PAGE=N
SNAPSHOT_PATH=${ARTIFACTS_ROOT}/snapshots
```

Enable action snapshots when additional evidence is useful while developing or troubleshooting a test:

```text
CAPTURE_ACTION_SNAPSHOTS=Y
```

## Snapshot files

Snapshot evidence is stored under `SNAPSHOT_PATH` and organized by evidence type:

```text
${SNAPSHOT_PATH}/
├── screenshots/
├── html/
└── metadata/
```
