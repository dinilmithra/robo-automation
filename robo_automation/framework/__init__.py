"""Generic Playwright wrapper objects."""

from .robo_browser_context import RoboBrowserContext
from .robo_page import RoboPage
from .robo_locator import RoboLocator
from .types import BrowserSession, Scope

__all__ = ["BrowserSession", "RoboBrowserContext", "RoboPage", "RoboLocator", "Scope"]
