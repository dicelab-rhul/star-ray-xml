import re
import ast
from typing import Any
from lxml import etree as ET
from .query import XMLQueryError, Expr

XML_START_PATTERN = re.compile(r"^\s*<")


class _Element:
    """Wraps an `lxml` element (which may be full XML elements, their attributes, literals (e.g. text) or other properties) adding some additional functionality for use in implementations of `XMLState`. `XMLState` will handle the creation of instances of `_Element`, it is not part of the public API but is stable and documented regardless."""

    def __init__(self, base: ET.ElementBase):
        super().__init__()
        self._base = base

    def get_root(self) -> "_Element":
        """Retrieves the root element of the tree containing this element.

        Returns:
            _Element: The root element.
        """
        parent = self._base
        while parent:
            parent = parent.getparent()
        return _Element(parent)

    def get_parent(self) -> "_Element":
        """Retrieves the parent of this element if it exists.

        Returns:
            _Element: The parent element wrapper if available, otherwise None.
        """
        if self.is_literal:
            return None
        parent = self._base.getparent()
        if parent is None:
            return None
        return _Element(parent)

    def get_children(self) -> list["_Element"]:
        """Retrieves all direct children of this element.

        Returns:
            list[_Element]: A list of element wrappers for the children of this element.
        """
        return [_Element(child) for child in self._base.getchildren()]

    def get_attributes(self) -> dict[str, str]:
        """Retrieves all attributes of this element as a dictionary. This does not include special attributes (those prefixed with `@`) such as `@text`, `@tag`, etc.

        Returns:
            dict[str, str]: A dictionary containing attribute names and their corresponding values.
        """
        # TODO what about special attributes like @text, @tail or @prefix ?
        return dict(**self._base.attrib)

    def xpath(self, xpath: str, namespaces: dict[str, str]) -> list["_Element"]:
        """Evaluates an XPath expression from this element.

        Args:
            xpath (str): The XPath query string (see https://www.w3schools.com/xml/xpath_intro.asp for details on xpath queries)
            namespaces (dict[str, str]): A dictionary of namespace prefixes to XML URIs.

        Returns:
            list[_Element]: A list of elements matching the XPath query (empty if there was no match).
        """
        elements = self._base.xpath(xpath, namespaces=namespaces)
        if not isinstance(elements, list):
            elements = [elements]
        return [_Element(element) for element in elements]

    def index(self, element: "_Element") -> int:
        """Returns the index of the specified child element relative to this element.

        Args:
            element (_Element): The child element.

        Returns:
            int: The index of the child element.
        """
        return self._base.index(element._base)

    @property
    def prefix(self) -> str:
        """Retrieves the namespace prefix of this element, if any.

        Returns:
            str: The namespace prefix or the last segment of the default namespace URI if no explicit prefix is set.
        """
        prefix = self._base.prefix
        if prefix is None:
            # it is using the default namespace, fin
            prefix = self._base.nsmap[None].rsplit("/", 1)[-1]
        return prefix

    @property
    def tag(self) -> str:
        """Retrieves the tag of the element, excluding its namespace.

        Returns:
            str: The tag name of the element.
        """
        return self._base.tag.rsplit("}", 1)[-1]

    @property
    def name(self) -> str:
        """The qualified name of the element, combining the prefix and the tag.

        Returns:
            str: The fully qualified name of the element.
        """
        return f"{self.prefix}:{self.tag}"

    @property
    def text(self) -> str:
        """Retrieves the text content of this element.

        Returns:
            str: The text content of the element.
        """
        return self._base.text

    @text.setter
    def text(self, value: Any) -> None:
        """Sets the text content of this element to a string representation of the value.

        Args:
            value (Any): The text content
        """
        if isinstance(value, Expr):
            value = value.eval(self)
        self._base.text = str(value)

    @property
    def tail(self) -> str:
        """Retrieves the tail text of this element (text following this element).

        Returns:
            str: The tail text of the element.
        """
        return self._base.tail

    @tail.setter
    def tail(self, value: Any):
        """Sets the tail text of this element.

        Args:
                    value (Any): The text to set as the tail.
        """
        if isinstance(value, Expr):
            value = value.eval(self)
        self._base.tail = str(value)

    @property
    def head(self) -> str:
        """Retrieves the head text (text immediately preceding this element).

        Returns:
            str: The head text of the element.
        """
        prev = self._base.getprevious()
        if prev is None:
            parent = self._base.getparent()
            return parent.text
        else:
            return prev.tail

    @head.setter
    def head(self, value: Any):
        """Sets the head text of this element's parent or previous sibling.

        Args:
                    value (Any): The text to set as the head.
        """
        if isinstance(value, Expr):
            value = value.eval(self)
        prev = self._base.getprevious()
        if prev is None:
            parent = self._base.getparent()
            parent.text = value
        else:
            prev.tail = value

    def get(
        self, key: str, default: Any = None
    ) -> str | int | bool | float | list | dict | tuple:
        """Retrieves the value of an attribute or returns a default value if the attribute does not exist.

        Args:
            key (str): The attribute name.
            default (Any): The default value to return if the attribute is not found.

        Returns:
            Any: The value of the attribute, evaluated to a Python literal if possible, or the default value.
        """
        return _Element.literal_eval(self._base.get(key, default=default))

    def set(self, key: str, value: Any):
        """Sets the value of an attribute.

        Args:
            key (str): The attribute name.
            value (Any): The new value for the attribute.
        """
        if isinstance(value, Expr):
            value = value.eval(self)
        return self._base.set(key, str(value))

    def replace(self, old_element: "_Element", new_element: "_Element"):
        """Replaces an old child element with a new element.

        Args:
            old_element (_Element): The element to be replaced.
            new_element (_Element): The new element.
        """
        return self._base.replace(old_element._base, new_element._base)

    def insert(self, index: int, element: "_Element"):
        """Inserts an element at a specified index among this element's children.

        Args:
            index (int): The index at which the new element should be inserted.
            element (_Element): The element to insert.
        """
        return self._base.insert(index, element._base)

    def remove(self, element: "_Element"):
        """Removes a specific child element from this element.

        Args:
            element (_Element): The element to remove.
        """
        return self._base.remove(element._base)

    def remove_attribute(self, attribute_name: str):
        """Removes an attribute from this element.

        This does not work with special attributes (prefixed with `@`). Use the corresponding methods:
        - `@text` : `remove_text`
        - `@tail` : `remove_tail`
        - `@head` : `remove_head`
        Other special attributes (`@prefix`, `@tag` `@name`) cannot be removed.

        Args:
            attribute_name (str): The name of the attribute to remove.
        """
        del self._base.attrib[attribute_name]

    def remove_text(self):
        """Removes the text content of this element (sets the text to the empty string)."""
        self._base.text = None

    def remove_tail(self):
        """Removes the tail text content of this element (sets the text to the empty string)."""
        self._base.tail = None

    def remove_head(self):
        """Removes the head text content of this element (sets the text to the empty string)."""
        # TODO implement removal of head text
        raise NotImplementedError("TODO implement removal of head text")

    def is_orphaned(self, root: "_Element"):
        """Determines if this element is orphaned (is not connected to a specified root element).

        Args:
            root (_Element): The root element to check against.

        Returns:
            bool: `True` if this element is orphaned relative to the provided root, `False` otherwise.
        """
        parent = self._base
        while parent is not None:
            parent = parent.getparent()
            if parent == root._base:
                return False
        return True

    def __hash__(self):
        return self._base.__hash__()

    def __eq__(self, other):
        return self._base.__eq__(other)

    def __str__(self):
        return str(self._base)

    @property
    def attribute_name(self):
        """Retrieves the name of the attribute if this element is an attribute.

        Returns:
            str: The attribute name.
        """
        return self._base.attrname

    @property
    def is_attribute(self):
        """Checks if this element is an attribute node.

        Returns:
            bool: True if this element is an attribute node, otherwise False.
        """
        return self._base.is_attribute

    @property
    def is_head(self):
        """Checks if this element represents head text.

        Returns:
            bool: True if this element represents head text, otherwise False.
        """
        # TODO however, generally we should prefer to use is_text or is_tail and this check is more expensive...
        raise NotImplementedError("TODO check if this is a head")

    @property
    def is_text(self):
        """Checks if this element represents text content.

        Returns:
            bool: True if this element represents text content, otherwise False.
        """
        return self._base.is_text

    @property
    def is_tail(self):
        """Checks if this element represents tail text.

        Returns:
            bool: True if this element represents tail text, otherwise False.
        """
        return self._base.is_tail

    @property
    def is_literal(self):
        """Checks if this element is a literal value (int, float, or bool).

        Returns:
            bool: True if this element is a literal value, otherwise False.
        """
        return isinstance(self._base, int | float | bool)

    @property
    def is_unicode_result(self):
        """Checks if this element is a unicode result (this typically means the element is a text element, or is some other `str` result from an xpath query).

        Returns:
            bool: True if the element is an unicode result (see `lxml` docs for more details), otherwise False.
        """
        return isinstance(self._base, ET._ElementUnicodeResult)

    @property
    def is_element(self):
        """Checks if this element is a full xml element (i.e. is fully enclosed with `</>`).

        Returns:
            bool: True if the element represents a full xml element, otherwise False.
        """
        return isinstance(self._base, ET._Element)

    @property
    def nsmap(self):
        """Retrieves the namespace mapping for the element (if it is a full element).

        Returns:
            dict: A dictionary representing the namespace prefix to URI mapping.
        """
        return self._base.nsmap

    def as_string(self) -> str:
        """Converts the element to a canonical string representation.

        Returns:
                    str: A canonical string representation of the element.
        """
        return ET.tostring(
            self._base,
            method="c14n",
        ).decode("UTF-8")

    def as_literal(self):
        """Converts this element to a Python literal (only valid for unicode elements or attributes).

        Returns:
                    Any: The Python literal value of the element.

        Raises:
                    XMLQueryError: If the element cannot be converted to a literal.
        """
        if self.is_literal:
            return self._base
        elif self.is_unicode_result:
            return _Element.literal_eval(self._base)
        else:
            raise XMLQueryError(f"Failed to convert element {self} to literal.")

    def iter_parents(self):
        """Generator that traverses upward through the element tree yielding each parent element.

        Yields:
            _Element: The next parent element.
        """
        parent = self._base
        while parent:
            parent = parent.getparent()
            yield _Element(parent)

    @staticmethod
    def literal_eval(
        value: str,
    ) -> str | int | float | bool | list | tuple | dict | None:
        """Safely evaluates a string to a Python literal (str, int, float, bool, list, tuple, dict) if possible.

        Args:
            value (str): The string to evaluate.

        Returns:
            str | int | float | bool | list | tuple | dict | None: The evaluated Python literal, or the original string if evaluation fails - this means it could not be evalated to a python literal. Will return `None` if `None` is provided.
        """
        if value is None:
            return None
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return str(value)
