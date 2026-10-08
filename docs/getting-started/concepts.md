# Core Concepts

`robo-automation` owns generic browser automation infrastructure. It does not know which business application is being tested.

## Resource model

```text
Browser
  ↓
RoboBrowserContext
  ↓
RoboPage
  ↓
RoboLocator
```

Higher-level libraries can specialize these wrappers without recreating browser lifecycle.

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
