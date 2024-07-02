""" TODO """

import re
import ast
from typing import Dict, List, Any, Tuple, Type
from copy import deepcopy
from functools import wraps

from lxml import etree as ET
from pydantic import BaseModel

from star_ray.pubsub._pubsub import Subscriber
from star_ray.utils.literal_eval import literal_eval_with_ops
from star_ray.pubsub import EventPublisher, TopicPublisher
from star_ray.event import Event

from .query import Select, Update, Delete, Replace, Insert, XPathQueryError


TEXT = "@text"
TAIL = "@tail"
HEAD = "@head"
TAG = "@tag"  # <svg:g/> tag = "g"
NAME = "@name"  #  <svg:g/> name = "svg:g"
PREFIX = "@prefix"


class XMLElementChangePublisher(TopicPublisher):

    def subscribe(self, topic: Tuple[str, Type[Event]], subscriber: Subscriber) -> None:
        topic = (topic[0], EventPublisher.fully_qualified_name(topic[1]))
        return super().subscribe(topic, subscriber)

    def unsubscribe(
        self, topic: Tuple[str, Type[Event]], subscriber: Subscriber
    ) -> None:
        topic = (topic[0], EventPublisher.fully_qualified_name(topic[1]))
        return super().unsubscribe(topic, subscriber)

    def notify_subscribers(self, message: Tuple["_Element", Event]) -> None:
        element_id = message[0].get("id", None)
        if not element_id is None:
            topic = (element_id, EventPublisher.fully_qualified_name(type(message[1])))
            new_attributes = message[0].get_attributes()
            for sub in self._subscribers[topic]:
                sub.__notify__(deepcopy(new_attributes))


class _format_dict_expr(dict):
    def __missing__(self, key):
        if key != "value":
            raise KeyError(key)
        return "{value}"


class _format_dict_template(dict):
    def __missing__(self, key):
        return f"{{{key}}}"


class Template(BaseModel):  # TODO test this

    expr: str

    def __init__(self, expr: str, **values: Dict[str, Any]):
        expr = expr.format_map(_format_dict_template(values))
        super().__init__(expr=expr)

    def eval(self, element: "_Element", _: Any):
        expr = self.expr.format_map(element.get_attributes())
        result = literal_eval_with_ops(expr)
        return result


class Expr(Template):

    def __init__(self, expr: str, **values: Dict[str, Any]):
        assert "value" not in values  # "value" is a reserved key
        try:
            expr = expr.format_map(_format_dict_expr(values))
        except KeyError as e:
            raise KeyError(
                f"Key: `{e.args[0]}` missing from {Expr.__name__}: `{expr}`"
            ) from e
        super().__init__(expr=expr)

    def eval(self, _: "_Element", value: Any):
        expr = self.expr.format(value=value)
        return literal_eval_with_ops(expr)


def set_xpath_on_exception(fun):
    @wraps(fun)
    def _set_xpath_on_exception(*args):
        try:
            return fun(*args)
        except XPathQueryError as e:
            e.kwargs["xpath"] = args[1].xpath
            raise

    return _set_xpath_on_exception


XML_START_PATTERN = re.compile(r"^\s*<")


class _Element:

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
        return dict(**self._base.attrib)

    def xpath(self, xpath: str, namespaces: Dict[str, Any]) -> Any:
        return self._base.xpath(xpath, namespaces=namespaces)

    def index(self, element: "_Element"):
        return self._base.index(element._base)

    @property
    def prefix(self):
        prefix = self._base.prefix
        if prefix is None:
            # it is using the default namespace, fin
            prefix = self._base.nsmap[None].rsplit("/", 1)[-1]
        return prefix

    @property
    def tag(self):
        return self._base.tag.rsplit("}", 1)[-1]

    @property
    def name(self):
        return f"{self.prefix}:{self.tag}"

    @property
    def text(self):
        return self._base.text

    @text.setter
    def text(self, value: Any):
        if isinstance(value, Template):
            value = value.eval(self, self.text)
        self._base.text = str(value)

    @property
    def tail(self):
        return self._base.tail

    @tail.setter
    def tail(self, value: Any):
        if isinstance(value, Template):
            value = value.eval(self, self.tail)
        self._base.tail = str(value)

    @property
    def head(self):
        prev = self._base.getprevious()
        if prev is None:
            parent = self._base.getparent()
            return parent.text
        else:
            return prev.tail

    @head.setter
    def head(self, value: Any):
        if isinstance(value, Template):
            value = value.eval(self, self.head)
        prev = self._base.getprevious()
        if prev is None:
            parent = self._base.getparent()
            parent.text = value
        else:
            prev.tail = value

    def get(self, key: str, default: Any = None):
        return _Element.literal_eval(self._base.get(key, default=default))

    def set(self, key: str, value: Any):
        # print(key, value)
        if isinstance(value, Template):
            value = value.eval(self, self._base.get(key, default=None))
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
        while not parent is None:
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
    def literal_eval(value: Any):
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
            raise XPathQueryError(f"Failed to convert element {self} to literal.")

    def __str__(self):
        return str(self._base)

    def _iter_parents(self):
        parent = self._base
        while parent:
            parent = parent.getparent()
            yield _Element(parent)


class XMLState(EventPublisher):
    """A class to represent and manipulate XML data."""

    def __init__(
        self,
        xml: str,
        namespaces: Dict[str, str] = None,
        parser: ET.XMLParser = None,
    ):
        super().__init__()
        if parser is None:
            parser = ET.XMLParser(remove_comments=True)
        self._parser = parser
        self._root = _Element(
            ET.fromstring(xml, parser=self._parser)
        )  # pylint: disable=I1101
        self._namespaces = dict() if namespaces is None else namespaces

    def __str__(self):
        return str(ET.tostring(self._root._base, method="c14n2", with_comments=False))

    def xpath(self, xpath: str) -> Any:
        return self._root.xpath(xpath, namespaces=self._namespaces)

    def get_root(self) -> _Element:
        return self._root

    def get_namespaces(self):
        return self._namespaces

    @set_xpath_on_exception
    def update(self, query: Update):
        elements = self.xpath(query.xpath)
        if not isinstance(elements, list):
            elements = [elements]
        for element in elements:
            XMLState.update_element_attributes(_Element(element), query.attrs)
        self.notify_subscribers(query)

    @set_xpath_on_exception
    def insert(self, query: Insert):
        elements = self.xpath(query.xpath)
        if not isinstance(elements, list):
            elements = [elements]
        if len(elements) == 0:
            raise XPathQueryError(
                "Invalid xpath: `{xpath}` for `insert`, no parent element was found at this path.",
            )
        if len(elements) > 1:
            raise XPathQueryError(
                "Invalid xpath: `{xpath}` for `insert`, found {elements_length} but only 1 is allowed.",
                elements_length=len(elements),
            )
        XMLState.insert_in_element(
            _Element(elements[0]),
            query,
            parser=self._parser,
            # inherit_namespaces=self._inherit_namespaces,
        )
        self.notify_subscribers(query)

    @set_xpath_on_exception
    def replace(self, query: Replace):
        elements = self.xpath(query.xpath)
        if not isinstance(elements, list):
            elements = [elements]
        if len(elements) > 1:
            raise XPathQueryError(
                "Invalid xpath: `{xpath}` for `insert`, found {elements_length} but only 1 is allowed.",
                elements_length=len(elements),
            )
        # TODO self.notify_subscribers(query)
        raise NotImplementedError("TODO")

        # XMLState.insert_in_element(
        #     _Element(elements[0]),
        #     query,
        #     parser=self._parser,
        #     inherit_namespaces=self._inherit_namespaces,
        # )

    @set_xpath_on_exception
    def delete(self, query: Delete):
        elements = self.xpath(query.xpath)
        if not isinstance(elements, list):
            elements = [elements]
        if len(elements) > 1:
            raise XPathQueryError(
                "Invalid xpath: `{xpath}` for `insert`, found {elements_length} but only 1 is allowed.",
                elements_length=len(elements),
            )
        XMLState.delete_element(_Element(elements[0]))
        self.notify_subscribers(query)

    @set_xpath_on_exception
    def select(self, query: Select):
        elements = self.xpath(query.xpath)
        if not isinstance(elements, list):
            elements = [elements]
        result = [
            XMLState.select_from_element(_Element(element), query)
            for element in elements
        ]
        self.notify_subscribers(query)
        return result

    @staticmethod
    def update_element_attributes(element: _Element, attrs: Dict[str, Any]):
        if not element.is_node:
            raise XPathQueryError(
                "Failed to update: `{element}` is not an xml element, xpath: `{xpath}`",
                element=element,
            )
        for attr, value in attrs.items():
            if not attr.startswith("@"):
                element.set(attr, value)
            elif attr == TEXT:
                element.text = value
            elif attr == TAIL:
                element.tail = value
            elif attr == HEAD:
                element.head = value
            elif attr == TAG:
                raise XPathQueryError(
                    "Cannot update tag on an element, xpath: `{xpath}`"
                )
            elif attr == PREFIX:
                raise XPathQueryError(
                    "Cannot update namespace prefix on an element, xpath: `{xpath}`"
                )

    @staticmethod
    def _replace_element(
        element: _Element,
        xml: str,
        parser: ET.XMLParser,
    ):
        parent = element.get_parent()
        if parent is None:
            raise NotImplementedError(
                "replacing the XML root node is not yet supported."
            )
        replace = XMLState._new_element(
            xml,
            parser=parser,
        )
        parent.replace(element, replace)

    @staticmethod
    def _update_unicode_element(element: _Element, value: Any):
        parent = element.get_parent()
        if element.is_attribute:
            parent.set(element.attribute_name, value)
        elif element.is_text:
            parent.text = value
        elif element.is_tail:
            parent.tail = value
        else:
            # who knows what happened if this occurs
            raise XPathQueryError(
                "Failed to update unicode element: `{element}` unknown element type, xpath: `{xpath}`",
                element=element,
            )

    @staticmethod
    def insert_in_element(
        element: _Element,
        query: Insert,
        parser: ET.XMLParser,
        # inherit_namespaces: bool,
    ):
        if element.is_node:
            if XML_START_PATTERN.match(query.element):
                child = XMLState._new_element(query.element, parser=parser)
                element.insert(query.index, child)
            else:
                XMLState._insert_text_at(element, query.element, index=query.index)
        else:
            raise XPathQueryError(
                "Failed to insert into xpath result: `{element}` must be an xml element, xpath: `{xpath}`",
                element=element,
            )

    @staticmethod
    def _insert_text_at(element: _Element, text: str, index: int):
        if index > 0:
            children = element.get_children()
            children[index - 1].tail = text
        else:
            element.text = text

    @staticmethod
    def _new_element(
        xml: str,
        # parent: _Element,
        parser: ET.XMLParser,
        # inherit_namespaces: bool = True,
    ) -> _Element:
        return _Element(ET.fromstring(xml, parser=parser))

        # if inherit_namespaces and parent.nsmap:
        #     # The new element is assumed to be part of the default namespace,
        #     # This is mostly for sanity as xpath queries do not return what we might expect after manually inserting an element,
        #     # this is a know issue with lxml see for example: https://stackoverflow.com/questions/69888767/why-does-lxml-etree-subelement-allow-making-elements-which-are-not-serialisabl
        #     xmlns = " ".join(f'xmlns:{k}="{v}"' for k, v in parent.nsmap.items() if k)
        #     default_xmlns = f'xmlns="{parent.nsmap[None]}"'
        #     namespaced_xml = f"""<_dummy {default_xmlns} {xmlns}>{xml}</_dummy>"""
        #     return _Element(next(iter(ET.fromstring(namespaced_xml, parser=parser))))
        # else:

    @staticmethod
    def delete_element(element: _Element):
        if element.is_literal:
            raise XPathQueryError(
                "Failed to delete xpath result: `{element}` is a literal, xpath: `{xpath}`",
                element=element,
            )
        elif element.is_node:
            element.get_parent().remove(element)
        elif element.is_attribute:
            element.get_parent().remove_attribute(element.attribute_name)
        elif element.is_text:
            element.get_parent().remove_text()
        elif element.is_tail:
            element.get_parent().remove_tail()
        else:
            # who knows what happened if this occurs
            raise XPathQueryError(
                "Failed to delete xpath result: `{element}` unknown element type, xpath: `{xpath}`",
                element=element,
            )

    @staticmethod
    def _delete_element_attributes(element: _Element, attrs: List[str]):
        for attr in attrs:
            if not attr.startswith("@"):
                element.remove_attribute(attr)
            elif attr == TEXT:
                element.remove_text()
            elif attr == TAIL:
                element.remove_tail()
            elif attr == TAG:
                # this is not a valid attribute to delete, all elements must have a name.
                raise XPathQueryError(
                    "Cannot delete tag from an element. To delete an element use `attrs = None`, xpath: `{xpath}`"
                )
            elif attr == PREFIX:
                # this is not a valid attribute to delete, all elements must have a name.
                raise XPathQueryError(
                    "Cannot delete namespace prefix from an element. To delete an element use `attrs = None`, xpath: `{xpath}`"
                )

    @staticmethod
    def select_from_element(element: _Element, query: Select):
        if element.is_node:
            if query.attrs:
                return dict(XMLState._iter_element_attributes(element, query.attrs))
            else:
                return element.as_string()
        elif element.is_result:
            if query.attrs:
                raise XPathQueryError(
                    "Failed to select attributes: `{element}` is not an xml element, xpath: `{xpath}`",
                    element=element,
                )
            else:
                return element.as_literal()
        elif element.is_literal:
            return element.as_literal()  # this is already a primitive value
        else:
            # TODO could be a string or int value if an attribute is selected
            raise XPathQueryError(
                "Failed to select xpath result: `{element}`, xpath: `{xpath}`",
                element=element,
            )

    @staticmethod
    def _iter_element_attributes(element: _Element, attrs: List[str]):
        for attr in attrs:
            if not attr.startswith("@"):
                yield attr, element.get(attr, None)
            elif attr == TAG:
                yield attr, element.tag
            elif attr == NAME:
                yield attr, element.name
            elif attr == PREFIX:
                yield attr, element.prefix
            elif attr == TEXT:
                yield attr, element.text
            elif attr == TAIL:
                yield attr, element.tail
