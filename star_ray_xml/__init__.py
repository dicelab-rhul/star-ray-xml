"""The `star_ray_xml` package is an extension of [`star_ray`](https://github.com/dicelab-rhul/star-ray) that uses XML as the description language for the state of an environment. It supports read/write queries of the XML state via [xpath](https://www.w3schools.com/xml/xpath_intro.asp), providing a language with which agents can take actions and observe their environment.

Important classes:
    `XMLState` : which defines the public API which an `Ambient` may use to access the underlying state.
    `_XMLState` : the default (internal) implementation of `XMLState` that is backed by the well-known `lxml` package.
    `XMLAmbient` : the default implementation of an `Ambient` (see `star_ray` package) that makes use of XML as its state description language. It exposes the standard `__update__`, `__select__` API and is read and mutated via `XMLQuery` events (see below).

Query classes:
    Select : Read-only query that selects (retrieves) elements and their attributes from the XML state.
    Update : Write query that will update element attributes.
    Replace : Write query that will replace entire elements.
    Delete : Write query that will delete elements or their attributes.
    Insert : Write query that will insert new elements.
    XMLQuery : The base class for all queries, defines the `__execute__` method which is the method that effectively defines how the query mutates (or reads) the state. It provides direct access to the `XMLState` API and may be subclassed to provide more user-friendly queries, especially where the operation may require access to various XML attributes which might otherwise require additional queries (these instead can be read or written to directly).

See the documentation in each class for details on their use. These queries can also be constructed using the following factory methods: [`select`, `update`, `replace`, `delete`, `insert`] which provide some conveniences.
"""

from .query import (
    select,
    insert,
    delete,
    replace,
    update,
    Expr,
    Select,
    Insert,
    Delete,
    Replace,
    Update,
    XMLQuery,
    XPathQuery,
    XMLQueryError,
)
from .state import XMLState, _XMLState
from .ambient import XMLAmbient
from .sensor import XMLSensor

__all__ = (
    "XMLAmbient",
    "XMLState",
    "_XMLState",
    "XMLSensor",
    "select",
    "insert",
    "delete",
    "replace",
    "update",
    "Select",
    "Insert",
    "Delete",
    "Replace",
    "Update",
    "Expr",
    "Expr",
    "XMLQuery",
    "XPathQuery",
    "XMLQueryError",
)
