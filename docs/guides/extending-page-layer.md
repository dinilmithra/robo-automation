# Extending the Page Layer

Higher-level libraries should specialize the generic page rather than duplicate Playwright lifecycle. The Appian layer is the reference pattern: `AppianPage` wraps `RoboPage`, `AppianLocator` derives from `RoboLocator`, and the Appian pytest plugin wraps the lower-layer `robo_page` as `appian_page`. Both page wrappers transparently preserve the underlying Playwright `Page` API.

This keeps browser/context/page creation in the generic layer while allowing domain-specific behavior to remain in the domain library.
