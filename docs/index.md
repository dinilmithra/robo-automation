# robo-automation

`robo-automation` is the shared infrastructure layer for browser automation projects.

If you are writing normal application tests through a higher-level library such as `robo-appian`, you may never need to use this library directly.

## What it handles

- starting and closing browser resources;
- pytest fixtures;
- common page/locator wrappers;
- logging and testcase correlation;
- browser diagnostics and artifacts;
- performance monitoring;
- runtime configuration.

## Configuration rule

Every configurable subsystem follows the same idea:

```text
fixture override
    ↓
environment variable
    ↓
library default
```

If the consumer provides nothing, the library defaults are used.

## Where to start

- **Application developer:** use the higher-level library for your application, such as `robo-appian`.
- **Framework developer:** read Core Concepts, Pytest Fixtures, Runtime Configuration and Framework Architecture.
