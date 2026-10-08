# robo-automation

Generic browser automation infrastructure shared by application test projects.

## Owns

- testcase/process/attempt correlation IDs
- logging context and per-test logs
- pytest-friendly performance monitoring
- generic Playwright/browser lifecycle
- `RoboBrowserContext`, `RoboPage`, `RoboLocator`, and `Scope`
- pytest fixtures for `performance_monitor`, the Playwright runtime, `browser`, `storage_state`, `context_options`, `wait_time`, `context_page_handler`, `context`, `robo_page`, and `page`
- the installed `pytest11` plugin entry point (`robo_automation = "robo_automation.pytest_plugin"`)

The public resource chain is:

```text
Playwright Browser
    ↓
RoboBrowserContext
    ↓
RoboPage
    ↓
RoboLocator
```

`wait_time` is expressed in **seconds**. `robo-automation` converts it to milliseconds only when calling Playwright timeout APIs.

`robo_page` owns the generic page lifecycle. Higher-level libraries can specialize that page without recreating its Playwright lifecycle. For standalone `robo-automation` use, a conditional plugin alias exposes `page -> robo_page`; when the `robo-appian` plugin is loaded, that generic alias is not registered so `robo-appian` can expose the Appian-specialized public `page` deterministically.

## Does not own

- application login or business workflows
- CORE/CIN concepts
- Appian-specific component behavior

Python imports use `robo_automation`; the distribution/library name is `robo-automation`.

## Publishing

`robo-automation` is a standalone distribution. CORE currently pins `robo-automation==0.1.7`; publish a compatible release before Jenkins or other published-package consumers depend on newer framework APIs.

From the parent workspace, with a Python 3.12 environment that contains Poetry:

```powershell
python .\robo-automation\tools\publish_robo_automation.py --build-only
python .\robo-automation\tools\publish_robo_automation.py
```

The publisher increments the patch version by default, removes any existing `dist/` directory before the build, builds into a temporary output directory, and then stages fresh artifacts. Pass an explicit Poetry version rule/version to override the default patch increment. `--build-only` still increments and keeps the new version.

Publishing helpers are excluded from the distribution.

## Local development environment

Create a dedicated Python 3.12 environment for this library:

```powershell
py -3.12 .\robo-automation\tools\setup_venv.py
.\robo-automation\.venv\Scripts\Activate.ps1
```

The setup script installs Poetry into the library `.venv`, runs `poetry lock` to refresh an out-of-date lock file, and then runs `poetry install`. You do not need to regenerate `poetry.lock` manually after changing `pyproject.toml` before running the bootstrap.

Run commands through Poetry when the environment is not activated:

```powershell
poetry run pytest
poetry run black .
```

## Relationship to robo-appian

`robo-appian` depends on these generic abstractions and contains Appian-specific components and interaction helpers. `robo-automation` must not import `robo-appian` or CORE application code.
