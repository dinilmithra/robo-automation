# Extending the Page Layer

Higher-level libraries should specialize the generic page rather than duplicate Playwright lifecycle. The Appian layer is the reference pattern: `AppianPage` derives from `RoboPage`, `AppianLocator` derives from `RoboLocator`, and the Appian pytest plugin specializes the lower-layer `robo_page` as `appian_page`.

This keeps browser/context/page creation in the generic layer while allowing domain-specific behavior to remain in the domain library.
