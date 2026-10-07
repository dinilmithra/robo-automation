from unittest.mock import MagicMock, Mock

from playwright.sync_api import Locator, Page

from robo_automation import RoboLocator, RoboPage


def _mock_page() -> Page:
    page = MagicMock(spec=Page)
    locator = MagicMock(spec=Locator)
    page.locator.return_value = locator
    return page


def test_get_wraps_playwright_page_without_public_bridge() -> None:
    page = _mock_page()
    robo_page = RoboPage.get(page)
    assert isinstance(robo_page, RoboPage)
    assert not hasattr(type(robo_page), "page")


def test_get_by_attributes_returns_robo_locator() -> None:
    page = _mock_page()
    robo_page = RoboPage.get(page)
    result = robo_page.get_by_attributes(
        attributes={"role": "button", "aria-label": "User options"},
        excat_match=True,
    )
    assert isinstance(result, RoboLocator)
    page.locator.assert_called_once_with(
        "xpath=.//*[@role='button' and @aria-label='User options']"
    )


def test_get_by_id_returns_robo_locator() -> None:
    page = _mock_page()
    robo_page = RoboPage.get(page)
    result = robo_page.get_by_id("jsAcceptButton", excat_match=True)
    assert isinstance(result, RoboLocator)
    page.locator.assert_called_once_with("xpath=.//*[@id='jsAcceptButton']")


def test_locator_class_can_be_specialized() -> None:
    class CustomLocator(RoboLocator):
        pass

    class CustomPage(RoboPage):
        locator_class = CustomLocator

    page = _mock_page()
    custom_page = CustomPage.get(page)
    result = custom_page.get_by_id("example")
    assert isinstance(result, CustomLocator)


def test_specialize_preserves_underlying_page() -> None:
    page = Mock(spec=Page)

    class SpecializedPage(RoboPage):
        pass

    robo_page = RoboPage.get(page)
    specialized = robo_page.specialize(SpecializedPage)

    assert isinstance(specialized, SpecializedPage)
    assert specialized.same_page(robo_page)
    assert specialized.specialize(SpecializedPage) is specialized


def test_robo_locator_exists_uses_match_count() -> None:
    page = _mock_page()
    robo_page = RoboPage.get(page)
    result = robo_page.get_by_id("un")
    result.locator.count.return_value = 1

    assert result.exists() is True

    result.locator.count.return_value = 0
    assert result.exists() is False
