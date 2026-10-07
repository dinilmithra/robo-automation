# Installation

`robo-automation` requires Python 3.12 and Playwright 1.63.0. Install the published package with your project dependency manager. For sibling-workspace development, use an editable path dependency so Python source edits are immediately visible.

```powershell
poetry add --editable ../robo-automation
```

Editable installs automatically reflect Python source changes, but distribution metadata changes (version, dependencies, or `pytest11` entry points) require an install/refresh.

Verify the active source and metadata:

```powershell
python -c "import importlib.metadata as m, robo_automation; print(m.version('robo-automation')); print(robo_automation.__file__)"
```

## Bootstrap a standalone development environment

From the workspace root:

```powershell
py -3.12 .\robo-automation\tools\setup_venv.py
```

The bootstrap recreates `.venv`, installs Poetry 2.5.1, runs `poetry lock`, and then runs `poetry install`. Running `poetry lock` before installation prevents setup from failing when `pyproject.toml` has changed since the previous lock file was generated.
