"""Generic attribute-based element wrapper."""

from __future__ import annotations

import re
from typing import Any, Mapping

from playwright.sync_api import Locator, expect

from .types import Scope


class RoboLocator:
    """Wrap an element located by arbitrary HTML attributes.

    ``attributes`` is an unrestricted HTML-attribute map used to build a
    scoped XPath locator. This lets callers describe HTML markup directly
    with attributes such as ``role``, ``aria-label``, ``data-testid``,
    ``title``, ``id``, ``href``, or application-specific ``data-*``
    attributes without browser automation maintaining an attribute whitelist.

    String values are matched exactly by default. Set ``excat_match=False``
    to use substring matching for string attribute values. Boolean values have
    presence semantics: ``True`` requires the attribute to exist and ``False``
    requires it to be absent. ``None`` also means the attribute must exist.

    Example::

        user_options = RoboLocator(
            scope,
            attributes={
                "role": "button",
                "aria-label": "User options",
            },
            excat_match=True,
        )
        user_options.to_be_visible()
        user_options.click()

    Args:
        scope: Playwright ``Page`` or ``Locator`` used as the search root.
        attributes: One or more HTML attributes used to identify the element.
            Attribute names are used directly in the XPath expression, so
            standard, ARIA, ``data-*``, and application-specific attributes
            are supported.
        excat_match: Attribute string matching mode. ``True`` (or ``None``)
            uses exact equality. ``False`` uses XPath ``contains()`` matching.
            This is a browser automation matching option and is not an element
            attribute.

    Raises:
        ValueError: If ``attributes`` is empty or an attribute name is invalid.
    """

    _ATTRIBUTE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")

    def __init__(
        self,
        scope: Scope,
        attributes: Mapping[str, Any],
        excat_match: bool | None = None,
    ) -> None:
        self.scope = scope
        self.attributes = dict(attributes)
        self.excat_match = excat_match
        self._locator = self._build_locator(self.attributes, excat_match)

    @staticmethod
    def _xpath_literal(value: str) -> str:
        """Return ``value`` as a safe XPath string literal."""
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'

        parts = value.split("'")
        literals: list[str] = []
        for index, part in enumerate(parts):
            if part:
                literals.append(f"'{part}'")
            if index < len(parts) - 1:
                literals.append('"\'"')
        return f"concat({', '.join(literals)})"

    def _build_locator(
        self,
        attributes: Mapping[str, Any],
        excat_match: bool | None,
    ) -> Locator:
        """Build the underlying scoped XPath locator."""
        if not attributes:
            raise ValueError("RoboLocator attributes must not be empty.")

        predicates: list[str] = []
        use_exact_match = excat_match is not False

        for name, value in attributes.items():
            if not isinstance(name, str) or not self._ATTRIBUTE_NAME.fullmatch(name):
                raise ValueError(f"Invalid RoboLocator attribute name: {name!r}")

            attribute = f"@{name}"

            if value is None or value is True:
                predicates.append(attribute)
                continue
            if value is False:
                predicates.append(f"not({attribute})")
                continue

            literal = self._xpath_literal(str(value))
            if use_exact_match:
                predicates.append(f"{attribute}={literal}")
            else:
                predicates.append(f"contains({attribute}, {literal})")

        predicate = " and ".join(predicates)
        return self.scope.locator(f"xpath=.//*[{predicate}]")

    @classmethod
    def get(
        cls,
        scope: Scope,
        attributes: Mapping[str, Any] | None = None,
        excat_match: bool | None = None,
    ) -> "RoboLocator":
        """Create a root or attribute-based ``RoboLocator``.

        When ``attributes`` is omitted, the returned ``RoboLocator`` represents
        the supplied search root and can be passed to :meth:`get_by_attributes`.
        When ``attributes`` is provided, this remains a convenience factory for
        creating the matching attribute-based locator directly.

        Args:
            scope: Playwright ``Page`` or ``Locator`` used as the search root.
            attributes: Optional HTML attributes used to identify an element.
            excat_match: Attribute string matching mode. ``True`` (or ``None``)
                uses exact equality; ``False`` uses substring matching.

        Returns:
            A root ``RoboLocator`` when ``attributes`` is omitted, otherwise a
            ``RoboLocator`` wrapping the matching element.
        """
        if attributes is not None:
            return cls(scope, attributes=attributes, excat_match=excat_match)

        result = object.__new__(cls)
        result.scope = scope
        result.attributes = {}
        result.excat_match = excat_match
        if isinstance(scope, Locator):
            result._locator = scope
        else:
            # A Page has no element identity of its own. Use the document root
            # as the locator search root for subsequent get_by_attributes calls.
            result._locator = scope.locator("html")
        return result

    @classmethod
    def get_by_attributes(
        cls,
        scope: Scope | "RoboLocator",
        attributes: Mapping[str, Any],
        excat_match: bool | None = None,
    ) -> "RoboLocator":
        """Create a locator below ``scope`` using arbitrary HTML attributes.

        ``scope`` may be a Playwright ``Page``/``Locator`` or another
        ``RoboLocator``. Passing a root ``RoboLocator`` created by
        ``RoboLocator.get(page)`` keeps chained lookup code uniform.

        Args:
            scope: Search root. A ``RoboLocator`` uses its currently retained
                Playwright locator as the search root.
            attributes: One or more HTML attributes used to identify the element.
            excat_match: Attribute string matching mode. ``True`` (or ``None``)
                uses exact equality; ``False`` uses substring matching.

        Returns:
            A ``RoboLocator`` wrapping the matching element.
        """
        search_scope: Scope = scope.locator if isinstance(scope, cls) else scope
        return cls(search_scope, attributes=attributes, excat_match=excat_match)

    @classmethod
    def get_by_id(
        cls,
        scope: Scope,
        element_id: str,
        excat_match: bool | None = None,
    ) -> "RoboLocator":
        """Create a ``RoboLocator`` located by its HTML ``id`` attribute.

        Args:
            scope: Playwright ``Page`` or ``Locator`` used as the search root.
            element_id: HTML ``id`` attribute value to locate.
            excat_match: Matching mode for the id value. ``True`` (or ``None``)
                uses exact equality; ``False`` uses substring matching.

        Returns:
            A ``RoboLocator`` wrapping the matching element.

        Raises:
            ValueError: If ``element_id`` is empty.
        """
        if not isinstance(element_id, str) or not element_id.strip():
            raise ValueError("RoboLocator element_id must not be empty.")

        return cls(
            scope,
            attributes={"id": element_id},
            excat_match=excat_match,
        )

    @property
    def locator(self) -> Locator:
        """Return the wrapped Playwright ``Locator``."""
        return self._locator

    def click(self, **kwargs: Any) -> None:
        """Click the wrapped element."""
        self._locator.click(**kwargs)

    def fill(self, value: str, **kwargs: Any) -> None:
        """Fill the wrapped element with ``value``."""
        self._locator.fill(value, **kwargs)

    def press(self, key: str, **kwargs: Any) -> None:
        """Press a key on the wrapped element."""
        self._locator.press(key, **kwargs)

    def check(self, **kwargs: Any) -> None:
        """Check the wrapped checkbox or radio element."""
        self._locator.check(**kwargs)

    def uncheck(self, **kwargs: Any) -> None:
        """Uncheck the wrapped checkbox element."""
        self._locator.uncheck(**kwargs)

    def exists(self) -> bool:
        """Return whether the wrapped locator currently matches any element."""
        return self._locator.count() > 0

    def is_visible(self, **kwargs: Any) -> bool:
        """Return whether the wrapped element is visible."""
        return self._locator.is_visible(**kwargs)

    def to_be_visible(
        self,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Assert visibility and narrow to the single visible match when unique.

        framework can render duplicate hidden and visible copies of the same
        control. This method filters the wrapped locator by visibility. When
        exactly one visible element exists, the wrapped locator is narrowed to
        that element so later operations such as :meth:`click` act on it.

        If more than one visible match exists, the wrapped locator is narrowed
        to the visible match set. A later strict Playwright operation such as
        :meth:`click` will still fail because the element remains ambiguous,
        or :meth:`first` can be used explicitly to select the first visible
        match.

        Args:
            timeout: Optional timeout in milliseconds. When ``None``, the
                timeout argument is omitted so Playwright uses its configured
                default assertion timeout.
            **kwargs: Additional keyword arguments forwarded to Playwright's
                ``LocatorAssertions.to_be_visible`` method.
        """
        visible_locator = self._locator.filter(visible=True)

        # When multiple visible matches exist, retain only the visible set.
        # A direct strict Playwright action such as click() will still fail on
        # ambiguity, while first() can be used explicitly to select one.
        if visible_locator.count() > 1:
            self._locator = visible_locator
            return

        # Use first only for the wait itself so a zero-match locator can wait
        # until a visible element appears without strict-mode ambiguity.
        assertion = expect(visible_locator.first)
        if timeout is None:
            assertion.to_be_visible(**kwargs)
        else:
            assertion.to_be_visible(timeout=timeout, **kwargs)

        if visible_locator.count() == 1:
            self._locator = visible_locator.first

    def first(self) -> "RoboLocator":
        """Return a new ``RoboLocator`` wrapping the first current match.

        This operates on the locator currently retained by this instance.
        After :meth:`to_be_visible`, that means the first visible match when
        multiple visible elements remain. The original ``RoboLocator`` is not
        modified.

        Returns:
            A new ``RoboLocator`` wrapping Playwright's ``Locator.first``.
        """
        first_locator = self._locator.first
        result = object.__new__(type(self))
        result.scope = self.scope
        result.attributes = dict(self.attributes)
        result.excat_match = self.excat_match
        result._locator = first_locator
        return result

    def is_enabled(self, **kwargs: Any) -> bool:
        """Return whether the wrapped element is enabled."""
        return self._locator.is_enabled(**kwargs)

    def is_checked(self, **kwargs: Any) -> bool:
        """Return whether the wrapped checkbox or radio element is checked."""
        return self._locator.is_checked(**kwargs)

    def inner_text(self, **kwargs: Any) -> str:
        """Return the rendered inner text of the wrapped element."""
        return self._locator.inner_text(**kwargs)

    def text_content(self, **kwargs: Any) -> str | None:
        """Return the text content of the wrapped element."""
        return self._locator.text_content(**kwargs)

    def get_attribute(self, name: str, **kwargs: Any) -> str | None:
        """Return an attribute from the wrapped element."""
        return self._locator.get_attribute(name, **kwargs)

    def wait_for_attribute(
        self,
        attributes: Mapping[str, Any],
        timeout: float | None = None,
    ) -> None:
        """Wait until one or more HTML attributes have the expected values.

        ``attributes`` accepts any valid HTML attribute name, including ARIA,
        ``data-*``, standard, and application-specific attributes. Each
        attribute is asserted with Playwright's retrying ``to_have_attribute``
        assertion, so dynamic state changes such as ``aria-expanded="true"``
        becoming ``aria-expanded="false"`` are handled without manual polling.

        Args:
            attributes: Attribute/value pairs to wait for. Example:
                ``{"aria-expanded": "false", "data-state": "ready"}``.
            timeout: Optional timeout in milliseconds. When ``None``, the
                timeout argument is omitted so Playwright uses its configured
                default assertion timeout.

        Raises:
            ValueError: If ``attributes`` is empty or contains an invalid name.
        """
        if not attributes:
            raise ValueError("wait_for_attribute attributes must not be empty.")

        assertion = expect(self._locator)
        for name, value in attributes.items():
            if not isinstance(name, str) or not self._ATTRIBUTE_NAME.fullmatch(name):
                raise ValueError(f"Invalid RoboLocator attribute name: {name!r}")

            expected = str(value)
            if timeout is None:
                assertion.to_have_attribute(name, expected)
            else:
                assertion.to_have_attribute(name, expected, timeout=timeout)

    def wait_for(self, **kwargs: Any) -> None:
        """Wait for the wrapped element using Playwright locator semantics."""
        self._locator.wait_for(**kwargs)

    def __getattr__(self, name: str) -> Any:
        """Delegate advanced locator operations to the wrapped locator."""
        return getattr(self._locator, name)
