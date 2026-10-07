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
