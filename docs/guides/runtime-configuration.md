# Runtime configuration

`robo-automation` resolves runtime configuration from typed configuration objects. Consumers can normally configure the framework with environment variables; projects that need programmatic policy can override the public pytest fixtures.

Configuration precedence is:

1. consumer fixture override;
2. consumer environment variable;
3. immutable `robo-automation` default.

Boolean flags accept `1`, `true`, `yes`, `y`, or `on` (case-insensitive) as true. Any other non-empty value is false. Examples below use `Y` and `N` for readability.

## Browser and timeout flags

| Flag | Default | Usage |
| --- | --- | --- |
| `BROWSER` | `chromium` | Session browser: `chromium`, `firefox`, or `webkit`. |
| `HEAD_LESS` | `Y` | Run the session browser without a visible window. Set `N` for interactive local debugging. |
| `WAIT_TIME` | `90` | Default framework timeout in **seconds**. The resolved value is clamped to at least 1 second. |
| `ENABLE_BROWSER_LAUNCH_DELAY` | `N` | Enable process-safe launch pacing for parallel workers. |
| `BROWSER_LAUNCH_INTERVAL_SECONDS` | `0` | Minimum seconds between browser launches when launch pacing is enabled. `0` disables the delay. |
| `CACHE_PATH` | `artifacts/runtime/cache` | Directory used for the launch-pacing lock and timestamp files. Relative paths resolve from the pytest root. |

Example:

```ini
BROWSER=chromium
HEAD_LESS=Y
WAIT_TIME=90
ENABLE_BROWSER_LAUNCH_DELAY=Y
BROWSER_LAUNCH_INTERVAL_SECONDS=2
CACHE_PATH=artifacts/runtime/cache
```

`WAIT_TIME` is also the default used by semantic component actions unless a component supplies its own positive timeout. State queries such as Appian `is_enabled()` can define their own immediate/waiting semantics and should be documented by the higher-level component package.

## Logging flags

| Flag | Default | Usage |
| --- | --- | --- |
| `PYTEST_LOG_LEVEL` | `INFO` | Framework/file logging level. |
| `PYTEST_LOG_CLI_LEVEL` | unset | Optional console logging level. |
| `PYTEST_LOG_CLI_FORMAT` | unset | Optional pytest console log format. |
| `PYTEST_LOG_CLI_DATE_FORMAT` | unset | Optional pytest console date format. |
| `PYTEST_PARALLEL_LOG_TO_FILE` | `N` | Enable the correlated execution log file. |
| `PYTEST_PARALLEL_LOG_PATH` | `artifacts/logs/execution` | Execution-log directory. |
| `TESTCASE_LOG_ENABLED` | `Y` | Enable per-testcase log files. |
| `TESTCASE_LOG_PATH` | `artifacts/logs/testcases` | Per-testcase log directory. |

Example:

```ini
PYTEST_LOG_LEVEL=INFO
PYTEST_PARALLEL_LOG_TO_FILE=Y
TESTCASE_LOG_ENABLED=Y
```

## Artifact and snapshot flags

| Flag | Default | Usage |
| --- | --- | --- |
| `ARTIFACTS_ROOT` | `artifacts` | Root artifact directory. |
| `SNAPSHOT_PATH` | `artifacts/evidence/actions` | Action/failure snapshot root. |
| `CAPTURE_ACTION_SNAPSHOTS` | `N` | Capture before/after evidence for instrumented browser actions. |
| `CAPTURE_FAILURE_SNAPSHOTS` | `N` | Capture failure evidence when the failure is not already represented by action evidence. |
| `ACTION_SNAPSHOT_FULL_PAGE` | `N` | Use full-page screenshots for snapshot evidence. |

Paths support recursive `${VAR}` references. This makes a shared layout possible without hardcoding an absolute path:

```ini
ARTIFACTS_ROOT=../artifacts
EVIDENCE_PATH=${ARTIFACTS_ROOT}/evidence
SNAPSHOT_PATH=${EVIDENCE_PATH}/actions
CAPTURE_ACTION_SNAPSHOTS=N
CAPTURE_FAILURE_SNAPSHOTS=Y
ACTION_SNAPSHOT_FULL_PAGE=N
```

Referenced variables must exist and be non-empty. Unresolved, empty, cyclic, or excessively recursive references raise a configuration error instead of silently producing an incorrect path.

See [Action Snapshots](action-snapshots.md) for lifecycle, deduplication, and evidence layout.

## Performance flags

Performance monitoring is enabled by default and writes worker-aware telemetry beneath `PERF_MONITOR_PATH`.

| Flag | Default | Usage |
| --- | --- | --- |
| `PERF_MONITOR_ENABLED` | `Y` | Enable performance monitoring. |
| `PERF_MONITOR_ACTIONS` | `Y` | Measure supported browser actions. |
| `PERF_MONITOR_FRAMEWORK` | `Y` | Measure framework lifecycle operations. |
| `PERF_MONITOR_CONSOLE` | `N` | Emit qualifying timing records to the console. |
| `PERF_MONITOR_PATH` | `artifacts/logs/performance` | Performance output directory. |
| `PERF_MONITOR_INTERVAL` | `1.0` | Sampling interval in seconds; minimum `0.1`. |
| `PERF_MONITOR_FLUSH_EVERY` | `20` | Flush the JSONL stream after this many pending writes; minimum `1`. |
| `PERF_MONITOR_THRESHOLD_MS` | `500.0` | Minimum duration in milliseconds for threshold classification; minimum `0`. |
| `PERF_MONITOR_SLOW_MS` | `2000.0` | Duration in milliseconds classified as slow; minimum `0`. |
| `PERF_MONITOR_SUMMARY_LIMIT` | `50` | Maximum slowest-operation entries retained in summaries; minimum `1`. |
| `PERF_MONITOR_RUN_ID` | `run-unknown` | Correlation identifier for a performance run. Parallel controller startup creates a run id when one is not already supplied. |

Example:

```ini
PERF_MONITOR_ENABLED=Y
PERF_MONITOR_ACTIONS=Y
PERF_MONITOR_FRAMEWORK=Y
PERF_MONITOR_CONSOLE=N
PERF_MONITOR_THRESHOLD_MS=500
PERF_MONITOR_SLOW_MS=2000
```

See [Performance and Correlation](performance-correlation.md) for output and correlation behavior.

## Browser diagnostics configuration

The typed configuration model currently defines these settings:

`ENABLE_BROWSER_DIAGNOSTICS`, `BROWSER_DIAGNOSTICS_CONSOLE`, `BROWSER_DIAGNOSTICS_PAGE_ERRORS`, `BROWSER_DIAGNOSTICS_NETWORK`, `BROWSER_DIAGNOSTICS_NAVIGATION`, and `BROWSER_DIAGNOSTICS_PATH`.

They are exposed through `DiagnosticsConfig` / `robo_diagnostics_config`, but the current runtime does **not** install a browser-diagnostics capture service from these values. Treat them as reserved/configuration-only for now; setting them does not by itself produce diagnostic artifacts. This distinction prevents configuration availability from being mistaken for implemented capture behavior.

## Public configuration fixtures

The pytest plugin exposes these session-scoped fixtures:

- `robo_runtime_config`
- `robo_logging_config`
- `robo_diagnostics_config`
- `robo_performance_config`
- `robo_snapshot_config`
- `robo_artifact_paths`
- `wait_time`

For example, an environment can set `PYTEST_LOG_LEVEL=DEBUG` without writing pytest code. A consumer that needs a programmatic override can replace the relevant fixture:

```python
import pytest
from robo_automation import LoggingConfig


@pytest.fixture(scope="session")
def robo_logging_config() -> LoggingConfig:
    return LoggingConfig(level="DEBUG", parallel_file_enabled=True)
```

The fixture value is consumed by the corresponding runtime service and takes precedence over the environment-derived default.

## Configuration ownership

`robo_automation.config` owns translation of runtime environment variables into typed configuration objects. Runtime services consume those resolved objects. Early pytest bootstrap resolves environment/default configuration before normal fixtures exist; fixture resolution then reapplies the final consumer configuration for the session.
