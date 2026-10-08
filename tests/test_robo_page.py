from unittest.mock import MagicMock, Mock

from playwright.sync_api import Locator, Page

from robo_automation import RoboLocator, RoboPage


def _mock_page() -> Page:
    page = MagicMock(spec=Page)
    locator = MagicMock(spec=Locator)
    page.locator.return_value = locator
    return page


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


def test_is_framework_page_recognizes_page_wrapper() -> None:
    from types import SimpleNamespace

    from robo_automation import RoboPage, is_framework_page

    page = object.__new__(RoboPage)
    page._page = SimpleNamespace()

    assert is_framework_page(page) is True
    assert is_framework_page(object()) is False
