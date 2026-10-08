# Pytest Fixtures

A fixture is something pytest prepares for a test or for the test session.

For example, a test may ask for a page without creating the browser itself:

```python
def test_example(page):
    ...
```

## Common fixtures

`robo-automation` provides generic fixtures such as:

- `browser` — browser session infrastructure;
- `context` — browser context lifecycle;
- `robo_page` — generic page wrapper;
- `wait_time` — timeout in seconds;
- `performance_monitor` — optional performance monitoring.

Higher-level libraries may expose their own specialized `page` fixture while continuing to use these resources.

## Configuration fixtures

The library also exposes cohesive configuration fixtures:

- `robo_runtime_config`
- `robo_logging_config`
- `robo_diagnostics_config`
- `robo_performance_config`
- `robo_artifact_paths`

If the consumer does not override a fixture, its values come from environment variables when present and otherwise from library defaults.

A consumer fixture override has the highest precedence.

Example:

```python
import pytest
from robo_automation.config import LoggingConfig


@pytest.fixture(scope="session")
def robo_logging_config():
    return LoggingConfig(level="DEBUG")
```

Use fixture overrides for project policy. Do not copy/reimplement the browser lifecycle just to change one setting.
