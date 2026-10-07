# Framework Architecture

The dependency direction is intentionally one-way:

```text
Playwright
    ↓
robo-automation
    ↓
robo-appian (optional specialization)
    ↓
application project
```

`robo-automation` must never import `robo-appian` or application code. A Playwright `BrowserContext` is wrapped as `RoboBrowserContext`; pages created by the generic lifecycle are wrapped as `RoboPage`; locator-producing operations return `RoboLocator` while preserving concrete subclasses where supported.
