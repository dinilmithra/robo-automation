# Handling Errors

`robo-automation` exposes one public base exception for automation infrastructure failures:

```python
from robo_automation import RoboAutomationError
```

Most tests do **not** need to catch this exception. Let pytest fail normally so the report keeps the full traceback, screenshot, logs, and other evidence.

Catch it only when your application has a useful recovery action.

## Basic example

```python
from robo_automation import RoboAutomationError

try:
    run_automation_step()
except RoboAutomationError as error:
    print(error)
```

`str(error)` contains the short human-readable message.

## Error details

A `RoboAutomationError` can also provide:

- `error.code` — a short stable code for logs or conditional handling.
- `error.details` — structured diagnostic information such as a URL, action, or timeout.
- `error.to_dict()` — all public error information as a dictionary.

Example:

```python
try:
    run_automation_step()
except RoboAutomationError as error:
    print(error.code)
    print(error.details)
```

Do not write test logic that depends on the exact English wording of the error message. Use `code` when code needs to distinguish errors.

## Keep the original cause

Framework code should preserve the original error when translating a lower-level failure:

```python
try:
    low_level_operation()
except Exception as exc:
    raise RoboAutomationError(
        "Could not open the requested page",
        code="NAVIGATION_FAILED",
        details={"url": requested_url},
    ) from exc
```

The `raise ... from exc` keeps the original technical cause in the traceback for troubleshooting.

## When should I catch it?

Usually, do not catch it in a normal test.

Good reasons to catch it include:

- your application has an expected recovery path;
- you want to add business context and then re-raise;
- framework integration code needs to classify the error.

Avoid this pattern:

```python
try:
    run_test()
except RoboAutomationError:
    pass
```

It hides a real test failure.

## Appian users

If you use `robo-appian`, Appian-specific failures use `RoboAppianError`. It is also a `RoboAutomationError`, so a broad automation handler can catch both.
