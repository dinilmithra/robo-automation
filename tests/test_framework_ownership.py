from pathlib import Path

import robo_automation


def test_generic_wrappers_are_exported_from_robo_automation() -> None:
    assert robo_automation.RoboBrowserContext.__module__.startswith("robo_automation.")
    assert robo_automation.RoboPage.__module__.startswith("robo_automation.")
    assert robo_automation.RoboLocator.__module__.startswith("robo_automation.")


def test_robo_appian_no_longer_owns_generic_framework() -> None:
    appian_root = Path(__file__).resolve().parents[2] / "robo-appian" / "robo_appian"
    assert not (appian_root / "framework").exists()
    assert (appian_root / "pytest_plugin.py").exists()
