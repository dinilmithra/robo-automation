# Performance and Correlation

`robo-automation` provides pytest-aware performance monitoring and correlation identifiers for testcase, attempt, process, and xdist worker context. Performance monitoring is enabled by default.

## Typical configuration

```ini
PERF_MONITOR_ENABLED=Y
PERF_MONITOR_ACTIONS=Y
PERF_MONITOR_FRAMEWORK=Y
PERF_MONITOR_CONSOLE=N
PERF_MONITOR_PATH=artifacts/logs/performance
PERF_MONITOR_INTERVAL=1.0
PERF_MONITOR_THRESHOLD_MS=500
PERF_MONITOR_SLOW_MS=2000
PERF_MONITOR_SUMMARY_LIMIT=50
```

`PERF_MONITOR_ACTIONS` controls supported browser-action timing. `PERF_MONITOR_FRAMEWORK` controls framework lifecycle timing. Both feed the same worker-aware JSONL stream and summary model. `PERF_MONITOR_CONSOLE` can additionally emit qualifying timing records to the console.

The monitor periodically samples process metrics using `PERF_MONITOR_INTERVAL`. Buffered records are flushed according to `PERF_MONITOR_FLUSH_EVERY`. Threshold and slow-duration values are expressed in milliseconds.

## Parallel runs

Each worker writes correlated output without sharing browser/session state. During a parallel run the controller establishes `PERF_MONITOR_RUN_ID` when the consumer has not supplied one, and worker summaries are merged at session finalization. `PERF_MONITOR_SUMMARY_LIMIT` bounds the slowest-operation detail retained in summaries.

Correlation context is also used by logs and evidence so artifacts can be associated with the originating testcase, process/attempt, and worker.

See [Runtime Configuration](runtime-configuration.md) for the complete flag table and the API pages for `PytestPerformanceMonitor` and correlation helpers.
