# Runtime configuration

`robo-automation` treats configuration as part of the public runtime API rather
than allowing logging, diagnostics, and performance services to read environment
variables independently.

The precedence is:

1. consumer fixture override;
2. consumer environment variable;
3. immutable `robo-automation` library default.

A consumer that supplies neither an environment variable nor a fixture override
therefore receives a complete working library default.

## Public configuration fixtures

The pytest plugin exposes these session-scoped fixtures:

- `robo_runtime_config`
- `robo_logging_config`
- `robo_diagnostics_config`
- `robo_performance_config`
- `robo_artifact_paths`
- `wait_time`

For example, an environment can set `PYTEST_LOG_LEVEL=DEBUG` without writing any
pytest code. A consumer that needs a programmatic override can instead replace the
fixture:

```python
import pytest
from robo_automation import LoggingConfig

@pytest.fixture(scope="session")
def robo_logging_config() -> LoggingConfig:
    return LoggingConfig(level="DEBUG", parallel_file_enabled=True)
```

The fixture value is consumed by runtime logging services and therefore takes
precedence over the environment-derived default.

## Configuration ownership

Only `robo_automation.config` should translate environment variables into typed
configuration objects. Logging, performance, browser diagnostics, and artifact
services should consume those resolved objects and should not call `os.getenv`
directly.

Early `pytest_configure` bootstrap is the one lifecycle exception because normal
fixtures do not exist yet. The plugin builds an environment/default bootstrap
configuration there, then reapplies fixture-resolved runtime configuration once
session fixtures are available.
