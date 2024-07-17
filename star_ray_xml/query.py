"""TODO"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Any, TYPE_CHECKING
from pydantic import BaseModel
from star_ray.event import Action
from star_ray.utils.literal_eval import literal_eval_with_ops

if TYPE_CHECKING:
    from .state import XMLState, _Element

__all__ = ("XMLQuery", "XPathQuery", "Update")


# class _format_dict_expr(dict):
#     def __missing__(self, key):
#         if key != "value":
#             raise KeyError(key)
#         return "{value}"


class _format_dict_template(dict):
    def __missing__(self, key):
        return f"{{{key}}}"


class Expr(BaseModel):  # TODO test this
    expr: str

    def __init__(self, expr: str, **values: Dict[str, Any]):
        expr = expr.format_map(_format_dict_template(values))
        super().__init__(expr=expr)

    def eval(self, element: "_Element"):
        expr = self.expr.format_map(element.get_attributes())
        result = literal_eval_with_ops(expr)
        return result


# class Expr(Expr):

#     def __init__(self, expr: str, **values: Dict[str, Any]):
#         assert "value" not in values  # "value" is a reserved key
#         try:
#             expr = expr.format_map(_format_dict_expr(values))
#         except KeyError as e:
#             raise KeyError(
#                 f"Key: `{e.args[0]}` missing from {Expr.__name__}: `{expr}`"
#             ) from e
#         super().__init__(expr=expr)

#     def eval(self, _: "_Element", value: Any):
#         expr = self.expr.format(value=value)
#         return literal_eval_with_ops(expr)


class XMLQuery(ABC, Action):
    """Base class for XML queries."""

    @abstractmethod
    def __execute__(self, state: XMLState) -> Any:
        pass


class XMLQueryError(Exception):
    def __init__(self, message, **kwargs):
        super().__init__(message)
        self.kwargs = kwargs

    def __str__(self):
        return self.args[0].format(**self.kwargs)

    def __repr__(self):
        return str(self)


class XPathQuery(XMLQuery):
    """Base class for XML queries that use `xpath`."""

    xpath: str

    def is_read(self):
        raise NotImplementedError()

    def is_write(self):
        raise NotImplementedError()

    def is_write_tree(self):
        raise NotImplementedError()

    def is_write_element(self):
        raise NotImplementedError()


class Insert(XPathQuery):
    """Query to insert an XML element."""

    element: str
    index: int

    @staticmethod
    def new(xpath: str, element: str, index: int = 0):
        return Insert(
            xpath=xpath,
            element=element,
            index=index,
        )

    def is_read(self):
        return False

    def is_write(self):
        return True

    def is_write_tree(self):
        return True

    def is_write_element(self):
        return False

    def __execute__(self, state: XMLState) -> Any:
        return state.insert(self)


class Delete(XPathQuery):
    """Query to delete an XML element."""

    @staticmethod
    def new(xpath: str):
        return Delete(xpath=xpath)

    def is_read(self):
        return False

    def is_write(self):
        return True

    def is_write_tree(self):
        return True

    def is_write_element(self):
        return False

    def __execute__(self, state: XMLState) -> Any:
        return state.delete(self)


class Replace(XPathQuery):
    """Query to replace an XML element."""

    element: str

    @staticmethod
    def new(xpath: str, element: str):
        return Replace(xpath=xpath, element=element)

    def is_read(self):
        return False

    def is_write(self):
        return True

    def is_write_tree(self):
        return True

    def is_write_element(self):
        return False

    def __execute__(self, state: XMLState) -> Any:
        return state.replace(self)


class Update(XPathQuery):
    """Query to update XML element attributes."""

    attrs: Dict[str, int | float | bool | str | Expr | Expr]

    @staticmethod
    def new(xpath: str, attrs: Dict[str, Any]):
        return Update(xpath=xpath, attrs=attrs)

    def is_read(self):
        return False

    def is_write(self):
        return True

    def is_write_tree(self):
        return False

    def is_write_element(self):
        return True

    def __execute__(self, state: XMLState) -> Any:
        return state.update(self)


class Select(XPathQuery):
    """Query to select XML elements and their attributes."""

    attrs: List[str] | None

    @staticmethod
    def new(xpath: str, attrs: List[str] = None):
        return Select(xpath=xpath, attrs=attrs)

    def is_read(self):
        return True

    def is_write(self):
        return False

    def is_write_tree(self):
        return False

    def is_write_element(self):
        return False

    def __execute__(self, state: XMLState) -> Any:
        return state.select(self)


def insert(xpath: str, element: str, index: int = 0):
    return Insert(xpath=xpath, element=element, index=index)


def delete(xpath: str):
    return Delete(xpath=xpath)


def replace(xpath: str, element: str):
    return Replace(xpath=xpath, element=element)


def update(xpath: str, attrs: Dict[str, Any]):
    """Update XML data.

    Args:
        xpath (str): of the element(s) to update.
        attrs (Dict[str, Any]): element attributes to update.

    XML elements hold different kinds of data which can be updated as follows:
    - attributes      : `<attribute_name>` e.g. `id` or `width`
    - text            : `@text` this text appears INSIDE the element e.g. `<g>text</g>`
    - tail (text)     : `@tail` this text appears AFTER the element e.g. `<g></g>text`
    - head (text)     : `@head` this text appears BEFORE the element e.g. `text<g></g>`

    A note about updating text:
    An element `<g></g>` contains no text. Its text can be updated using the `@text` attribute, but it cannot be updated using an xpath containing `/text()'.
    An element `<g> </g>` contains the text " ", and can therefore be updated using both methods.

    There is currently no way to update the tag (element name) or namespace information of an element, this is due to an unfortunate limitation with `lxml`.
    """
    return Update(xpath=xpath, attrs=attrs)


def select(xpath: str, attrs: List[str] = None):
    """Select XML data.

    Args:
        xpath (str): of the element(s).
        attrs (List[str], optional): attributes to select. Defaults to None.

    XML elements hold different kinds of data which can be selected as follows:
    - tag             : `@tag`
    - prefix          : `@prefix` this is the namespace prefix e.g. `svg` in `svg:rect`
    - attributes      : `<attribute_name>` e.g. `id` or `width`
    - text            : `@text` this text appears INSIDE the element e.g. `<g>text<g>`
    - tail (text)     : `@tail` this text appears AFTER the element e.g. `<g><g>text`
    - child elements  : are select using the xpath query, e.g. //xml/rect/*, attrs should be `None`

    There are alternative ways to get the tag and text attributes using xpath directly (attrs should be `None`):
    - tag             : name(QUERY)  this will return the tag
    - text            : QUERY/text() this will return all string text in the element as a list (if it exists)

    All of the other built-in xpath functions (`count(...)` `sum(...)`, etc.) can be used to get element properties.

    It is also possible to get a single attribute using xpath directly (attrs should be `None`):
        xpath = "//svg:rect/@width
    by using `attrs` one can select multiple attributes with a single query.

    A known querk of selecting with /text():
        xpath = "//svg:g/text()"
        <g> </g> will return [" "]
        <g></g>  will return [] instead of what we might expect [""]

    Returns:
        Select: select query
    """
    return Select(xpath=xpath, attrs=attrs)
