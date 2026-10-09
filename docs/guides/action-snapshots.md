# Action Snapshots

Action snapshots provide optional, step-by-step browser evidence around supported Playwright actions. The feature is implemented by **robo-automation** and is available to higher-level libraries such as **robo-appian** because those libraries ultimately execute Playwright `Page` and `Locator` actions.

The feature is disabled by default because capturing screenshots and DOM content around every action increases execution time and artifact size.

## Enable action snapshots

Set the following in the consuming project's environment configuration:

```env
CAPTURE_ACTION_SNAPSHOTS=Y
SNAPSHOT_PATH=${EVIDENCE_PATH}/actions
```

Disable it with:

```env
CAPTURE_ACTION_SNAPSHOTS=N
```

Optional controls:

```env
# Persist the live DOM with each snapshot.
ACTION_SNAPSHOT_HTML=Y

# Capture a full-page screenshot instead of the current viewport.
ACTION_SNAPSHOT_FULL_PAGE=N
```

## Two-phase lifecycle

Every supported action has exactly two phases:

```text
before
  ↓
perform action
  ↓
after
```

There is **no separate `after_error` phase**. A failed action still produces its normal `after` snapshot. The metadata identifies the outcome.

Successful action:

```json
{
  "phase": "after",
  "status": "passed",
  "duration_ms": 128.415
}
```

Failed action:

```json
{
  "phase": "after",
  "status": "failed",
  "error_type": "TimeoutError",
  "error": "..."
}
```

The `before` snapshot uses `status: "started"`.

## Evidence written for each phase

Each phase can contain:

- PNG screenshot
- live HTML DOM, when `ACTION_SNAPSHOT_HTML=Y`
- JSON metadata

A typical pair looks like:

```text
00042__click__before__<process-id>.png
00042__click__before__<process-id>.html
00042__click__before__<process-id>.json

00042__click__after__<process-id>.png
00042__click__after__<process-id>.html
00042__click__after__<process-id>.json
```

Artifacts are separated by pytest-xdist worker and correlation/process ID so parallel workers do not overwrite each other.

## Metadata

The JSON metadata records enough context to correlate an action with the running test and its evidence. Fields include:

| Field | Meaning |
| --- | --- |
| `timestamp` | Capture time as an epoch timestamp |
| `worker` | pytest-xdist worker, such as `gw0` |
| `sequence` | Monotonic action sequence within the worker |
| `action` | Playwright operation such as `click`, `fill`, or `check` |
| `phase` | `before` or `after` |
| `status` | `started`, `passed`, or `failed` |
| `target` | Page URL or locator description |
| `url` | Current page URL |
| correlation fields | Current test/process correlation values supplied by `robo-automation` |
| `duration_ms` | Action duration for the `after` phase |
| `error_type` | Exception class when the action fails |
| `error` | Exception message when the action fails |

The monitor is diagnostic-only: if evidence capture itself fails, that capture failure does not replace or mask the browser action result.

## Supported browser actions

The monitor currently instruments these Playwright `Page` actions:

```text
goto
reload
go_back
go_forward
set_content
```

and these `Locator` actions:

```text
click
dblclick
fill
clear
press
press_sequentially
type
check
uncheck
set_checked
select_option
hover
focus
blur
set_input_files
drag_to
scroll_into_view_if_needed
```

Higher-level framework operations are captured when they invoke one or more of these actions.

## Relationship to failure evidence

`CAPTURE_ACTION_SNAPSHOTS` is intentionally independent from application-level failure evidence settings.

For example, CORE uses:

```env
CAPTURE_ACTION_SNAPSHOTS=N
CAPTURE_FAILURE_SNAPSHOTS=Y
```

This configuration captures normal test-failure evidence without capturing every browser action. If both are enabled, action-level evidence and test-level failure evidence are both retained.

`CAPTURE_FAILURE_SNAPSHOTS` is a CORE/application policy flag; it is not part of the generic `robo-automation` snapshot monitor.

## Performance and storage considerations

A large test suite can generate many files because each supported action produces a `before` and `after` pair. Recommended usage is:

- keep `CAPTURE_ACTION_SNAPSHOTS=N` for routine CI execution;
- enable it temporarily when diagnosing an interaction, rerendering, selector, timing, or state-transition problem;
- keep failure-level evidence enabled independently when required by the consuming project.

## Pytest integration

When the `robo-automation` pytest plugin is installed, the monitor is started automatically from the session-scoped `action_snapshot_monitor` fixture when the feature is enabled. Consumers do not need to manually wrap actions.

The configuration is available through the session-scoped `robo_action_snapshot_config` fixture for advanced consumers that need to inspect or override resolved settings.
