# Development

Use Python 3.12. The project provides `tools/setup_venv.py` for a dedicated environment.

```powershell
py -3.12 .\tools\setup_venv.py
poetry run pytest
poetry run black .
```

After changing package metadata such as the version or `pytest11` entry point, refresh the editable installation before validating metadata-based discovery.
