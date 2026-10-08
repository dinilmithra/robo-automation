# Pytest Fixtures

The plugin owns the generic fixture lifecycle. Important fixtures include `performance_monitor`, `robo_automation_playwright`, `browser`, `storage_state`, `context_options`, `wait_time`, `context_page_handler`, `context`, and `robo_page`.

Standalone `robo-automation` also exposes a public `page` alias for `robo_page`. When the `robo-appian` plugin is installed, that generic alias is suppressed so the Appian layer can expose its specialized `page` deterministically.

Application projects should override policy/input fixtures such as `storage_state`, `context_options`, `wait_time`, or their own public `page` behavior rather than recreating browser/context lifecycle.

## Runtime configuration fixtures

`robo-automation` exposes typed configuration at fixture boundaries so consumer
projects can override behavior without forking library code:

- `robo_runtime_config`
- `robo_logging_config`
- `robo_diagnostics_config`
- `robo_performance_config`
- `robo_artifact_paths`
- `robo_logging_service`
- `wait_time`

If a fixture is not overridden, its value comes from environment variables when
present and otherwise from the library default. A consumer fixture override has
the highest runtime precedence.
