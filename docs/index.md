# robo-automation

`robo-automation` is the generic automation layer shared by higher-level UI libraries and application test projects. It owns Playwright resource lifecycle, generic wrapper types, pytest integration, correlation, logging, and performance instrumentation. It contains no Appian or CORE business logic.

The resource chain is:

```text
Playwright Browser
    ↓
RoboBrowserContext
    ↓
RoboPage
    ↓
RoboLocator
```

Higher layers specialize rather than duplicate this lifecycle. `robo-appian` specializes `robo_page` as `AppianPage`; an application such as CORE can then add application login/navigation policy on top.
