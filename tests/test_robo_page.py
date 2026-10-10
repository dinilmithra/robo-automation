from unittest.mock import MagicMock, Mock

from playwright.sync_api import Locator, Page
import pytest

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


def test_robo_page_delegates_unimplemented_playwright_methods() -> None:
    page = _mock_page()
    expected = MagicMock(spec=Locator)
    page.get_by_label.return_value = expected
    robo_page = RoboPage.get(page)

    result = robo_page.get_by_label("Email", exact=True)

    assert result is expected
    page.get_by_label.assert_called_once_with("Email", exact=True)


def test_robo_page_exposes_playwright_page_properties() -> None:
    page = _mock_page()
    robo_page = RoboPage.get(page)

    assert robo_page.keyboard is page.keyboard


def test_robo_page_does_not_expose_raw_playwright_page_property() -> None:
    page = _mock_page()
    robo_page = RoboPage.get(page)

    with pytest.raises(AttributeError):
        _ = robo_page.playwright_page


def test_wait_for_text_visible_uses_default_timeout_and_exact_match() -> None:
    page = _mock_page()
    text_locator = MagicMock(spec=Locator)
    visible_locator = MagicMock(spec=Locator)
    first_locator = MagicMock(spec=Locator)
    page.get_by_text.return_value = text_locator
    text_locator.filter.return_value = visible_locator
    visible_locator.first = first_locator

    result = RoboPage.get(page).wait_for_text_visible("Ready")

    assert result is first_locator
    page.get_by_text.assert_called_once_with("Ready", exact=True)
    text_locator.filter.assert_called_once_with(visible=True)
    first_locator.wait_for.assert_called_once_with(state="visible")


def test_wait_for_text_visible_converts_timeout_seconds_to_milliseconds() -> None:
    page = _mock_page()
    text_locator = MagicMock(spec=Locator)
    visible_locator = MagicMock(spec=Locator)
    first_locator = MagicMock(spec=Locator)
    page.get_by_text.return_value = text_locator
    text_locator.filter.return_value = visible_locator
    visible_locator.first = first_locator

    RoboPage.get(page).wait_for_text_visible("Ready", timeout=8, exact=False)

    page.get_by_text.assert_called_once_with("Ready", exact=False)
    first_locator.wait_for.assert_called_once_with(state="visible", timeout=8000)
