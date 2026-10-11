# robo-automation for Automation Authors

If you are a Business Analyst automating an Appian business flow, **use `robo-appian` for page interactions**. You usually do not need to call `RoboPage`, `RoboLocator`, or browser lifecycle APIs directly.

`robo-automation` is the supporting runtime. It provides the infrastructure that lets your business test run consistently.

## What you normally use indirectly

When a test receives an Appian `page` fixture, the framework has already prepared the browser and page for you:

```python
from robo_appian import AppianPage


def test_business_flow(page: AppianPage) -> None:
    page.textbox("Description").fill("Example")
    page.button("Submit").click()
```

You do not need to create the browser, context, or page yourself.

## When to read robo-automation documentation

Use these docs when you need to understand:

- how pytest fixtures provide browser/page resources;
- how timeout and environment configuration work;
- where logs, screenshots, and failure evidence come from;
- how tests run in parallel;
- how to troubleshoot runtime/setup problems.

For buttons, textboxes, dates, dropdowns, tables, dialogs, links, and other Appian controls, use the `robo-appian` documentation instead.

## Timeout values

Framework timeout values are expressed in **seconds**. A project setting such as:

```text
WAIT_TIME=90
```

means 90 seconds. Consumer tests should not convert it to milliseconds.

## Project configuration

A test project can override public configuration fixtures when project policy requires it. Most individual business tests should not contain runtime configuration.

## Maintainer material

Architecture, extending the page layer, correlation internals, performance instrumentation, and library development are framework-maintainer topics. They are useful when changing the framework, but they are not required to author normal business-flow automation.
