# Core Concepts

## Generic ownership

`BrowserSession`, `RoboBrowserContext`, `RoboPage`, `RoboLocator`, and `Scope` are generic automation contracts/wrappers owned by `robo-automation`. Application-specific libraries should derive or specialize them without introducing an upward dependency from `robo-automation`.

## Timeout contract

The `wait_time` fixture is expressed in **seconds**. `robo-automation` performs the conversion to milliseconds only when assigning Playwright timeout values. Consumers must not multiply fixture values by 1000.

## Plugin discovery

The distribution registers `robo_automation.pytest_plugin` through the `pytest11` entry-point group. Consumers normally do not add `pytest_plugins` or `-p` declarations for it.
