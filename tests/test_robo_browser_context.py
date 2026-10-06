from unittest.mock import MagicMock

from playwright.sync_api import BrowserContext, Page

from robo_automation import RoboBrowserContext, RoboPage


def _mock_context() -> BrowserContext:
    context = MagicMock(spec=BrowserContext)
    page = MagicMock(spec=Page)
    context.new_page.return_value = page
    return context


def test_get_wraps_playwright_context_without_public_bridge() -> None:
    context = _mock_context()
    robo_browser_context = RoboBrowserContext.get(context)
    assert isinstance(robo_browser_context, RoboBrowserContext)
    assert not hasattr(type(robo_browser_context), "context")


def test_new_page_returns_robo_page() -> None:
    context = _mock_context()
    robo_browser_context = RoboBrowserContext.get(context)
    page = robo_browser_context.new_page()
    assert isinstance(page, RoboPage)
    context.new_page.assert_called_once_with()


def test_storage_state_delegates_to_context() -> None:
    context = _mock_context()
    context.storage_state.return_value = {"cookies": [], "origins": []}
    robo_browser_context = RoboBrowserContext.get(context)
    assert robo_browser_context.storage_state() == {"cookies": [], "origins": []}
