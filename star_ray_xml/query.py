"""Package defining XML query classes.

These include:
- The `XMLQuery` class, which should be the base class for all XML queries.
- The primitive XML queries: `Select`, `Update`, `Insert`, `Delete`, `Replace`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING
from pydantic import BaseModel
from star_ray.event import Action
from star_ray.utils.literal_eval import literal_eval_with_ops

if TYPE_CHECKING:
    from .state import XMLState, _Element

__all__ = (
    "XMLQuery",
    "XPathQuery",
    "Select",
    "Update",
    "Delete",
    "Replace",
    "Insert",
    "XMLQueryError",
    "XPathElementsNotFound",
)


class _format_dict_template(dict):
    def __missing__(self, key):
        return f"{{{key}}}"


class Expr(BaseModel):  # TODO test this
    """This class represents a simple expression that can be evaluated as part of an XML query.

    It uses `star_rays`'s `literal_eval_with_ops` function under the hood to evaluate an expression which follows python syntax. It can peform simple arithmetic operations on attributes of an element (which are resolved during execution).

    Variables are defined in single `{` or `}` as in pythons string formatting. Example expression: `Expr("{x} + {y}")` assuming `x` and `y` are attributes of the element that will be queried.

    Example:
        `Expr` can be used in an `Update` query:
        ```
           Update(xpath="/svg:rect", attrs={"width" : Expr("{width} + 10")})
        ```

    Note that special attributes (prefixed with `@`) are not currently supported.
    """

    expr: str

    def __init__(self, expr: str, **values: dict[str, Any]):
        expr = expr.format_map(_format_dict_template(values))
        super().__init__(expr=expr)

    def eval(self, element: _Element) -> Any:
        """Evaluate this expression given the element as context.

        Args:
            element (_Element): element to use as context.

        Returns:
            Any: the result of the evaluation, which is typically a python literal (e.g. int, float, bool, str, list, dict).
        """
        expr = self.expr.format_map(element.get_attributes())
        result = literal_eval_with_ops(expr)
        return result


class XMLQueryError(Exception):
    """Error that may occur during the execution of an `XMLQuery`."""

    def __init__(self, message, **kwargs):  # noqa
        super().__init__(message)
        self.kwargs = kwargs

    def __str__(self):  # noqa
        return self.args[0].format(**self.kwargs)

    def __repr__(self):  # noqa
        return str(self)


class XPathElementsNotFound(XMLQueryError):
    """Error that indicates that an `xpath` query found no elements."""


class XMLQuery(ABC, Action):
    """Base class for XML queries. Defines the `__execute__` api.

    `__execute__` will be called during the execution of this action in the `Ambient`. It is effectively the definition of this action.
    """

    @abstractmethod
    def __execute__(self, state: XMLState) -> Any:
        """Execute method that defines this action. In this method you have direct access to the `XMLState` and can read/write properties by using the avaliable methods. Typically this will involve executing more primitive XMLQueries (such as `Select` and `Update`).

        Args:
            state (XMLState): the current (XML) state of the environment.

        Returns:
            Any: The result of executing this query. For write operations this may be None. Typically for read operations this will be some xml data or derived data.
        """
        pass

    @property
    @abstractmethod
    def is_read(self):
        """Whether this action is READ ONLY."""
        pass

    @property
    @abstractmethod
    def is_write(self):
        """Whether this action mutates the XML state."""
        pass

    @property
    @abstractmethod
    def is_write_tree(self):
        """Whether this action mutates the XML tree (e.g. insert, replace or delete elements) or will mutate multiple elements simultaneously."""
        pass

    @property
    @abstractmethod
    def is_write_element(self):
        """Whether this action mutates XML attributes on a SINGLE ELEMENT. This is a stronger guarantee than `is_write_tree` and may mean that the action can be executed in parallel."""
        pass


class XPathQuery(XMLQuery):
    """Base class for XML queries that use `xpath`."""

    xpath: str


class XMLUpdateQuery(XMLQuery):
    """Base class that defines properties: `is_read`, `is_write`, `is_write_element`, `is_write_tree`, for events that will only ever write to elements attributes."""

    @property
    def is_read(self):  # noqa: D102
        return False

    @property
    def is_write(self):  # noqa: D102
        return True

    @property
    def is_write_tree(self):  # noqa: D102
        return False

    @property
    def is_write_element(self):  # noqa: D102
        return True


class Update(XPathQuery, XMLUpdateQuery):
    """Query to update XML element attributes."""

    attrs: dict[str, int | float | bool | str | Expr | Expr]

    @staticmethod
    def new(xpath: str, attrs: dict[str, Any]):
        """Factory method for `Update` with positional arguments.

        Args:
            xpath (str): xpath used to locate the element.
            attrs (dict[str, Any]): attributes to update.

        Returns:
            Update: update query.

        See:
            `update` for further details.
        """
        return Update(xpath=xpath, attrs=attrs)

    def __execute__(self, state: XMLState) -> Any:  # noqa: D105
        return state.update(self)


class Insert(XPathQuery):
    """Query to insert an XML element."""

    element: str
    index: int

    @staticmethod
    def new(xpath: str, element: str, index: int = 0):
        """Factory method for `Insert` with positional arguments.

        GOTCHA: the inserted `element` must contain all relevant namespace information and its tag (or name) should be qualified with a prefix. For example: `<svg:rect xmlns:svg="http://www.w3.org/2000/svg" .../>`. If this is not done then the element may not be properly resolved by future XML queries.

        Args:
            xpath (str): xpath used to locate the parent element where the given `element` will be inserted.
            element (str): element to insert.
            index (int): the index to insert at.

        Returns:
            Insert: insert query.

        See:
            `insert` for further details.
        """
        return Insert(
            xpath=xpath,
            element=element,
            index=index,
        )

    @property
    def is_read(self):  # noqa
        return False

    @property
    def is_write(self):  # noqa
        return True

    @property
    def is_write_tree(self):  # noqa
        return True

    @property
    def is_write_element(self):  # noqa
        return False

    def __execute__(self, state: XMLState) -> Any:  # noqa
        return state.insert(self)


class Delete(XPathQuery):
    """Query to delete an XML element."""

    @staticmethod
    def new(xpath: str):
        """Factory method for `Delete` with positional arguments.

        Args:
            xpath (str): the xpath of the element(s) to delete.

        Returns:
            Delete: the delete query.
        See:
            `delete` for further details.
        """
        return Delete(xpath=xpath)

    @property
    def is_read(self):  # noqa
        return False

    @property
    def is_write(self):  # noqa
        return True

    @property
    def is_write_tree(self):  # noqa
        return True

    @property
    def is_write_element(self):  # noqa
        return False

    def __execute__(self, state: XMLState) -> Any:  # noqa
        return state.delete(self)


class Replace(XPathQuery):
    """Query to replace an XML element."""

    element: str

    @staticmethod
    def new(xpath: str, element: str):
        """Factory method for `Replace` with positional arguments.

        GOTCHA: the `element` to be the replacement must contain all relevant namespace information and its tag (or name) should be qualified with a prefix. For example: `<svg:rect xmlns:svg="http://www.w3.org/2000/svg" .../>`. If this is not done then the element may not be properly resolved by future XML queries.

        Args:
            xpath (str): the xpath of the element(s) to replace, the result of which must be an XML element.
            element (str): element to replace with.

        Returns:
            Replace: the replace query.

        See:
            `replace` for further details.
        """
        return Replace(xpath=xpath, element=element)

    @property
    def is_read(self):  # noqa
        return False

    @property
    def is_write(self):  # noqa
        return True

    @property
    def is_write_tree(self):  # noqa
        return True

    @property
    def is_write_element(self):  # noqa
        return False

    def __execute__(self, state: XMLState) -> Any:  # noqa
        return state.replace(self)


class Select(XPathQuery):
    """Query to select XML elements and their attributes."""

    attrs: list[str] | None

    @staticmethod
    def new(xpath: str, attrs: list[str] = None):
        """Factory method for `Select` with positional arguments.

        Args:
            xpath (str): the xpath of the element(s) to select.
            attrs (list[str], optional): attributes to select. Defaults to None, which will cause the entire element to be selected.

        Returns:
            Select: the select query.

        See:
            `select` for further details.
        """
        return Select(xpath=xpath, attrs=attrs)

    @property
    def is_read(self):  # noqa
        return True

    @property
    def is_write(self):  # noqa
        return False

    @property
    def is_write_tree(self):  # noqa
        return False

    @property
    def is_write_element(self):  # noqa
        return False

    def __execute__(self, state: XMLState) -> Any:  # noqa
        return state.select(self)


def insert(xpath: str, element: str, index: int = 0):
    """TODO."""
    return Insert(xpath=xpath, element=element, index=index)


def delete(xpath: str):
    """TODO."""
    return Delete(xpath=xpath)


def replace(xpath: str, element: str):
    """TODO."""
    return Replace(xpath=xpath, element=element)


def update(xpath: str, attrs: dict[str, Any]):
    """Update XML data.

    Args:
        xpath (str): xpath used to locate the element.
        attrs (dict[str, Any]): attributes to update.

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


def select(xpath: str, attrs: list[str] = None):
    """Select XML data.

    Args:
        xpath (str): the xpath of the element(s) to select.
        attrs (list[str], optional): attributes to select. Defaults to None, which will cause the entire element to be selected.

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


# TODO do the others is_select_query, is_insert_query, is_replace_query, is_delete_query


def is_update_query(cls):
    """Class decorator that will automatically add relevant properties is_read, is_write, is_write_element, is_write_tree to a class treating it as an Update query."""

    @property
    def is_read(self):
        return False

    @property
    def is_write(self):
        return True

    @property
    def is_write_tree(self):
        return False

    @property
    def is_write_element(self):
        return True

    # Add the properties to the class
    cls.is_read = is_read
    cls.is_write = is_write
    cls.is_write_tree = is_write_tree
    cls.is_write_element = is_write_element

    return cls
