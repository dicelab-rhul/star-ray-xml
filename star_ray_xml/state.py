"""TODO"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from functools import wraps

from lxml import etree as ET

from .query import Select, Update, Delete, Replace, Insert, XMLQueryError
from ._element import _Element, XML_START_PATTERN

TEXT = "@text"  # inner text of the element
TAIL = "@tail"  # text that appears AFTER the element
HEAD = "@head"  # text that appears BEFORE the element
TAG = "@tag"  # <svg:g/> tag = "g"
NAME = "@name"  # <svg:g/> name = "svg:g"
PREFIX = "@prefix"  # <svg:g/> prefix = "svg"

__all__ = ("XMLState", "_XMLState")

# TODO?
# class XMLElementChangePublisher(TopicPublisher):

#     def subscribe(self, topic: Tuple[str, Type[Event]], subscriber: Subscriber) -> None:
#         topic = (topic[0], EventPublisher.fully_qualified_name(topic[1]))
#         return super().subscribe(topic, subscriber)

#     def unsubscribe(
#         self, topic: Tuple[str, Type[Event]], subscriber: Subscriber
#     ) -> None:
#         topic = (topic[0], EventPublisher.fully_qualified_name(topic[1]))
#         return super().unsubscribe(topic, subscriber)

#     def notify_subscribers(self, message: Tuple["_Element", Event]) -> None:
#         element_id = message[0].get("id", None)
#         if element_id is not None:
#             topic = (element_id, EventPublisher.fully_qualified_name(type(message[1])))
#             new_attributes = message[0].get_attributes()
#             for sub in self._subscribers[topic]:
#                 sub.__notify__(deepcopy(new_attributes))


def _set_xpath_on_exception(fun):
    """Utility method that sets the `xpath` attribute of an `XMLQueryError` if it is raised in a function."""

    @wraps(fun)
    def _set_xpath_on_exception(*args):
        try:
            return fun(*args)
        except XMLQueryError as e:
            e.kwargs["xpath"] = args[1].xpath
            raise

    return _set_xpath_on_exception


class XMLState(ABC):
    """A class to represent and manipulate XML data."""

    @abstractmethod
    def update(self, query: Update):
        pass

    @abstractmethod
    def insert(self, query: Insert):
        pass

    @abstractmethod
    def replace(self, query: Replace):
        pass

    @abstractmethod
    def delete(self, query: Delete):
        pass

    @abstractmethod
    def select(self, query: Select):
        pass


class _XMLState(XMLState):
    """Default implementation of `XMLState`. Underlying xml parsing and queries are handled by the `lxml` package."""

    def __init__(
        self,
        xml: str,
        namespaces: Dict[str, str] | None = None,
        parser: ET.XMLParser | None = None,
    ):
        super().__init__()
        if parser is None:
            parser = ET.XMLParser(remove_comments=True)
        self._parser = parser
        self._root = _Element(ET.fromstring(xml, parser=self._parser))
        self._namespaces = dict() if namespaces is None else namespaces

    def __str__(self):
        return str(ET.tostring(self._root._base, method="c14n2", with_comments=False))

    def xpath(self, xpath: str) -> List[_Element]:
        """Query inner xml using xpath producing a (possibly empty) list of elements that are the result of the query.

        Args:
            xpath (str): xpath query

        Returns:
            List[_Element]: elements that result from the query
        """
        return self._root.xpath(xpath, namespaces=self._namespaces)

    def get_root(self) -> _Element:
        return self._root

    def get_namespaces(self) -> Dict[str, str]:
        return self._namespaces

    @_set_xpath_on_exception
    def update(self, query: Update) -> None:
        elements = self.xpath(query.xpath)
        for element in elements:
            _XMLState.update_element_attributes(element, query.attrs)

    @_set_xpath_on_exception
    def insert(self, query: Insert) -> None:
        elements = self.xpath(query.xpath)
        if len(elements) == 0:
            raise XMLQueryError(
                "Invalid xpath: `{xpath}` for `insert`, no parent element was found at this path.",
            )
        if len(elements) > 1:
            raise XMLQueryError(
                "Invalid xpath: `{xpath}` for `insert`, found {elements_length} but only 1 is allowed.",
                elements_length=len(elements),
            )
        _XMLState.insert_in_element(
            elements[0],
            query,
            parser=self._parser,
            # inherit_namespaces=self._inherit_namespaces,
        )

    @_set_xpath_on_exception
    def replace(self, query: Replace) -> None:
        elements = self.xpath(query.xpath)
        if len(elements) > 1:
            raise XMLQueryError(
                "Invalid xpath: `{xpath}` for `insert`, found {elements_length} but only 1 is allowed.",
                elements_length=len(elements),
            )
        raise NotImplementedError(
            "TODO element replacement (`replace`) is not currently implement."
        )

    @_set_xpath_on_exception
    def delete(self, query: Delete) -> None:
        elements = self.xpath(query.xpath)
        if len(elements) > 1:
            raise XMLQueryError(
                "Invalid xpath: `{xpath}` for `delete`, found {elements_length} but only 1 is allowed.",
                elements_length=len(elements),
            )
        _XMLState.delete_element(elements[0])

    @_set_xpath_on_exception
    def select(self, query: Select) -> List[Any]:
        elements = self.xpath(query.xpath)
        result = [_XMLState.select_from_element(element, query) for element in elements]
        return result

    @staticmethod
    def update_element_attributes(element: _Element, attrs: Dict[str, Any]):
        if not element.is_element:
            raise XMLQueryError(
                "Failed to update: `{element}` is not an xml element. (xpath: `{xpath}`)",
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
                raise XMLQueryError(
                    "Cannot update tag on an element. (xpath: `{xpath}`)"
                )
            elif attr == PREFIX:
                raise XMLQueryError(
                    "Cannot update namespace prefix on an element. (xpath: `{xpath}`)"
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
                "Replacing the XML root node is not yet supported."
            )
        replace = _XMLState._new_element(
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
            # NOTE who knows what happened if this occurs, if it does more extensive testing is needed...
            raise XMLQueryError(
                "Failed to update unicode element: `{element}` unknown element type. (xpath: `{xpath}`)",
                element=element,
            )

    @staticmethod
    def insert_in_element(
        element: _Element,
        query: Insert,
        parser: ET.XMLParser,
        # inherit_namespaces: bool,
    ):
        if element.is_element:
            if XML_START_PATTERN.match(query.element):
                child = _XMLState._new_element(query.element, parser=parser)
                element.insert(query.index, child)
            else:
                _XMLState._insert_text_at(element, query.element, index=query.index)
        else:
            raise XMLQueryError(
                "Failed to insert into xpath result: `{element}` must be an xml element. (xpath: `{xpath}`)",
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
        parser: ET.XMLParser,
    ) -> _Element:
        # TODO implement this inside _Element, we want to avoid using ET everywhere in this class
        return _Element(ET.fromstring(xml, parser=parser))

    @staticmethod
    def delete_element(element: _Element):
        if element.is_literal:
            raise XMLQueryError(
                "Failed to delete element: `{element}` as it is a literal. (xpath: `{xpath}`)",
                element=element,
            )
        elif element.is_element:
            element.get_parent().remove(element)
        elif element.is_attribute:
            element.get_parent().remove_attribute(element.attribute_name)
        elif element.is_text:
            element.get_parent().remove_text()
        elif element.is_tail:
            element.get_parent().remove_tail()
        else:
            # who knows what happened if this occurs
            raise XMLQueryError(
                "Failed to delete xpath result: `{element}` unknown element type (xpath: `{xpath}`)",
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
            elif attr == HEAD:
                # TODO
                raise NotImplementedError(
                    "Removing the head is not implemented yet use @text or @tail for now."
                )
            elif attr == TAG:
                # this is not a valid attribute to delete, all elements must have a name.
                raise XMLQueryError(
                    "Cannot delete tag from an element. (xpath: `{xpath}`)"
                )
            elif attr == PREFIX:
                # this is not a valid attribute to delete, all elements must have a name.
                raise XMLQueryError(
                    "Cannot delete namespace prefix from an element. (xpath: `{xpath}`)"
                )

    @staticmethod
    def select_from_element(element: _Element, query: Select):
        if element.is_element:
            if query.attrs:
                return dict(_XMLState._iter_element_attributes(element, query.attrs))
            else:
                return element.as_string()
        elif element.is_unicode_result:
            if query.attrs:
                raise XMLQueryError(
                    "Failed to select attributes: `{element}` is not an xml element, xpath: `{xpath}`",
                    element=element,
                )
            else:
                return element.as_literal()
        elif element.is_literal:
            return element.as_literal()  # this is already a primitive value
        else:
            # TODO could be a string or int value if an attribute is select? test this
            raise XMLQueryError(
                "Failed to select xpath result: `{element}`, xpath: `{xpath}`",
                element=element,
            )

    @staticmethod
    def _iter_element_attributes(element: _Element, attrs: List[str]):
        """Get all attribute values from an element.

        Args:
            element (_Element): element to get attribute values from.
            attrs (List[str]): attributes to get

        Raises:
            XMLQueryError: if an unknown special attribute is provided as part of `attrs`.

        Yields:
            Tuple[str, Any] : the attribute name and value as (attr, value).
        """
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
            elif attr == HEAD:
                yield attr, element.head
            else:
                raise XMLQueryError(
                    f"Unknown special attribute: {attr}, must be one of: {TAG, NAME, PREFIX, TEXT, TAIL, HEAD}"
                )
