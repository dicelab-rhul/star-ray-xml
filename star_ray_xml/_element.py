import re
import ast
from typing import Any, Dict, List, Tuple
from lxml import etree as ET
from .query import XMLQueryError, Expr

XML_START_PATTERN = re.compile(r"^\s*<")


class _Element:
    """Wraps lxml elements adding some additional functionality for use in implementations of `XMLState`."""

    def __init__(self, base: ET.ElementBase):
        super().__init__()
        self._base = base

    def get_root(self):
        parent = self._base
        while parent:
            parent = parent.getparent()
        return _Element(parent)

    def get_parent(self):
        if self.is_literal:
            return None
        parent = self._base.getparent()
        if parent is None:
            return None
        return _Element(parent)

    def get_children(self):
        return [_Element(child) for child in self._base.getchildren()]

    def get_attributes(self):
        # TODO what about special attributes like @text, @tail or @prefix ?
        return dict(**self._base.attrib)

    def xpath(self, xpath: str, namespaces: Dict[str, str]) -> List["_Element"]:
        elements = self._base.xpath(xpath, namespaces=namespaces)
        if not isinstance(elements, list):
            elements = [elements]
        return [_Element(element) for element in elements]

    def index(self, element: "_Element") -> int:
        return self._base.index(element._base)

    @property
    def prefix(self) -> str:
        prefix = self._base.prefix
        if prefix is None:
            # it is using the default namespace, fin
            prefix = self._base.nsmap[None].rsplit("/", 1)[-1]
        return prefix

    @property
    def tag(self) -> str:
        return self._base.tag.rsplit("}", 1)[-1]

    @property
    def name(self) -> str:
        return f"{self.prefix}:{self.tag}"

    @property
    def text(self) -> str:
        return self._base.text

    @text.setter
    def text(self, value: Any) -> None:
        if isinstance(value, Expr):
            value = value.eval(self)
        self._base.text = str(value)

    @property
    def tail(self) -> str:
        return self._base.tail

    @tail.setter
    def tail(self, value: Any):
        if isinstance(value, Expr):
            value = value.eval(self)
        self._base.tail = str(value)

    @property
    def head(self) -> str:
        prev = self._base.getprevious()
        if prev is None:
            parent = self._base.getparent()
            return parent.text
        else:
            return prev.tail

    @head.setter
    def head(self, value: Any):
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
    ) -> str | int | bool | float | List | Dict | Tuple:
        return _Element.literal_eval(self._base.get(key, default=default))

    def set(self, key: str, value: Any):
        # print(key, value)
        if isinstance(value, Expr):
            value = value.eval(self)
        return self._base.set(key, str(value))

    def replace(self, old_element: "_Element", new_element: "_Element"):
        return self._base.replace(old_element._base, new_element._base)

    def insert(self, index: int, element: "_Element"):
        return self._base.insert(index, element._base)

    def remove(self, element: "_Element"):
        return self._base.remove(element._base)

    def remove_attribute(self, attribute_name: str):
        del self._base.attrib[attribute_name]

    def remove_text(self):
        self._base.text = None

    def remove_tail(self):
        self._base.tail = None

    def is_orphaned(self, root: "_Element"):
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

    @property
    def attribute_name(self):
        return self._base.attrname

    @property
    def is_attribute(self):
        return self._base.is_attribute

    # TODO is head?
    @property
    def is_text(self):
        return self._base.is_text

    @property
    def is_tail(self):
        return self._base.is_tail

    @property
    def is_literal(self):
        return isinstance(self._base, (int, float, bool))

    @property
    def is_result(self):
        return isinstance(self._base, ET._ElementUnicodeResult)

    @property
    def is_node(self):
        return isinstance(self._base, ET._Element)

    @property
    def nsmap(self):
        return self._base.nsmap

    def as_string(self) -> str:
        return ET.tostring(
            self._base,
            method="c14n",
        ).decode("UTF-8")

    @staticmethod
    def literal_eval(
        value: str,
    ) -> str | int | float | bool | List | Tuple | Dict | None:
        if value is None:
            return None
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return str(value)

    def as_literal(self):
        if self.is_literal:
            return self._base
        elif self.is_result:
            return _Element.literal_eval(self._base)
        else:
            raise XMLQueryError(f"Failed to convert element {self} to literal.")

    def __str__(self):
        return str(self._base)

    def _iter_parents(self):
        parent = self._base
        while parent:
            parent = parent.getparent()
            yield _Element(parent)
