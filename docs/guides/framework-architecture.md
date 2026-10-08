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

## Runtime infrastructure boundary

`robo-automation` owns cross-cutting runtime infrastructure. In particular, the
library owns typed runtime configuration, logging handler lifecycle, testcase and
xdist log routing, correlation, artifact path resolution for library services, and
performance telemetry.

Consumer projects should keep semantic messages in their own layer and use normal
Python logging (`logging.getLogger(__name__)`). They should not recreate logging
handlers or read robo-automation logging/performance environment variables inside
application code.

Configuration follows this precedence:

1. consumer fixture override;
2. consumer environment variable;
3. robo-automation library default.

`robo-appian` remains responsible for Appian component semantics and may emit
Appian-specific messages. CORE remains responsible for business/workflow messages
and CORE-specific reporting. Neither layer owns generic Python/pytest logging
infrastructure.
