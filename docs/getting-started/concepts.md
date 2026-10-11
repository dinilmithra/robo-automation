# Runtime Concepts

`robo-automation` owns generic browser automation infrastructure. For Appian business automation, `robo-appian` is the normal page-interaction API and uses this runtime underneath.

## Resource model (background)

```text
Browser
  ↓
RoboBrowserContext
  ↓
RoboPage
  ↓
RoboLocator
```

Higher-level libraries such as `robo-appian` specialize these wrappers without recreating browser lifecycle. A normal business test does not need to instantiate or call these wrappers directly.

## Timeout rule

`wait_time` is expressed in **seconds**.

Consumers should pass values such as:

```text
WAIT_TIME=90
```

Do not multiply the value by 1000 in consumer code. `robo-automation` converts it when calling Playwright APIs.

## Configuration rule

Configuration is resolved in this order:

```text
consumer fixture override
        ↓
environment variable
        ↓
library default
```

This means a new project can use the library defaults and only override the settings it actually needs.

## Advanced plugin details

The installed package registers its pytest plugin automatically. Normal test projects should not need to manually add `pytest_plugins` or `-p` declarations.
