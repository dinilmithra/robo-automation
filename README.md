# robo-automation

`robo-automation` provides shared browser and pytest infrastructure for automation projects.

Most application test developers do not need to call its internal services directly. Higher-level libraries such as `robo-appian` use it automatically.

## What it provides

- browser and page lifecycle;
- pytest fixtures;
- configurable wait time;
- logging and correlation;
- diagnostics and artifacts;
- performance monitoring;
- reusable `RoboPage` and `RoboLocator` wrappers.

It intentionally contains no application-specific business logic.

## Basic pytest use

When installed as a pytest plugin, the library can provide browser/page infrastructure automatically.

A higher-level library may replace the public page type while keeping the same browser lifecycle. For example:

```text
application test
      ↓
robo-appian AppianPage
      ↓
robo-automation browser lifecycle
      ↓
Playwright
```

## Configuration

Consumers can use the library without defining any configuration. Defaults are built in.

When a setting needs to change, precedence is:

```text
consumer fixture override
        ↓
environment variable
        ↓
library default
```

Example: if the consumer sets:

```text
PYTEST_LOG_LEVEL=ERROR
```

and does not override the logging fixture, the effective log level is `ERROR`.

## Common public fixtures

Important configuration/runtime fixtures include:

```text
robo_runtime_config
robo_logging_config
robo_diagnostics_config
robo_performance_config
robo_artifact_paths
wait_time
browser
context
robo_page
```

Application projects should override policy/configuration fixtures rather than reimplementing generic browser lifecycle.

## Layering rule

`robo-automation` should contain a feature only when it is application-independent.

- Generic browser/logging/diagnostics/performance → `robo-automation`
- Appian behavior → `robo-appian`
- Application workflow/login/business rules → consumer project

## Advanced documentation

Framework maintainers can continue with the Architecture, Runtime Configuration, Performance and API guides in `docs/`.
## Error handling

Consumer code can catch `RoboAutomationError` when it has a real recovery path. Normal pytest tests should usually let the exception propagate so reports keep the full failure evidence. See `docs/getting-started/error-handling.md`.

