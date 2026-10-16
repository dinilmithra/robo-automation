# Action and Failure Snapshots

Snapshots provide visual evidence of what happened while an automation test was running. They are useful when reviewing test results or investigating a failure.

Configure snapshot capture using:

```text
CAPTURE_ACTION_SNAPSHOTS=N
CAPTURE_FAILURE_SNAPSHOTS=Y
CAPTURE_SNAPSHOT_IMAGES=Y
CAPTURE_SNAPSHOT_HTML=Y
SNAPSHOT_FULL_PAGE=N
SNAPSHOT_PATH=${ARTIFACTS_ROOT}/snapshots
```

| Setting | Purpose |
| --- | --- |
| `CAPTURE_ACTION_SNAPSHOTS` | Capture screenshots before and after supported automation actions. |
| `CAPTURE_FAILURE_SNAPSHOTS` | Capture screenshot evidence when a test fails. |
| `CAPTURE_SNAPSHOT_IMAGES` | Include PNG images; default `Y`. Set `N` to skip PNG images. |
| `CAPTURE_SNAPSHOT_HTML` | Include live HTML DOM; default `Y`. Set `N` to skip HTML files. |
| `SNAPSHOT_FULL_PAGE` | Capture the full page instead of only the visible area. |
| `SNAPSHOT_PATH` | Folder where snapshot evidence is stored. The standard project setting is `${ARTIFACTS_ROOT}/snapshots`. |

## Recommended configuration

For normal automation execution, failure snapshots provide useful evidence without capturing screenshots for every action:

```text
CAPTURE_ACTION_SNAPSHOTS=N
CAPTURE_FAILURE_SNAPSHOTS=Y
CAPTURE_SNAPSHOT_IMAGES=Y
CAPTURE_SNAPSHOT_HTML=Y
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

`CAPTURE_SNAPSHOT_IMAGES=N` skips screenshots for both action and failure evidence.
HTML can separately be disabled using `CAPTURE_SNAPSHOT_HTML=N`; JSON metadata
remains enabled whenever action/failure evidence is captured. The
`screenshots/` directory is created only when images are enabled; existing PNG
files from earlier runs are not deleted by this setting.

`CAPTURE_SNAPSHOT_IMAGES` and `CAPTURE_SNAPSHOT_HTML` default to `Y`. Disabling
both produces metadata-only snapshots. The action/failure flags still determine
when evidence is captured. Disabled formats do not create their directories or
delete existing artifacts.
