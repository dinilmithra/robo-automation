# robo-automation

Generic browser automation infrastructure shared by application test projects.

## Owns

- testcase/process/attempt correlation IDs
- logging context and per-test logs
- pytest-friendly performance monitoring
- generic Playwright/pytest automation utilities
- generic pytest session fixtures: `performance_monitor`, `playwright`, and `browser`

## Does not own

- application login or business workflows
- CORE/CIN concepts
- Appian-specific component behavior

Python imports use `robo_automation`; the distribution/library name is `robo-automation`.

## Publishing

`robo-automation` is a standalone distribution, matching the deployment model used
by `robo-appian`. CORE currently depends on version `0.1.1`; publish newer releases before CORE/Jenkins consumes them.

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
