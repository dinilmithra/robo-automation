"""Generic Playwright wrapper objects."""

from .robo_browser_context import RoboBrowserContext
from .robo_page import RoboPage
from .robo_locator import RoboLocator
from .types import Scope

__all__ = ["RoboBrowserContext", "RoboPage", "RoboLocator", "Scope"]
