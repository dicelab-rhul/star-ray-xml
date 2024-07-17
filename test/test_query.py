import unittest
import re
from star_ray_xml import XMLState, XMLQueryError, select, delete, update, insert

XML = """
<svg:svg width="200" height="200" xmlns:svg="http://www.w3.org/2000/svg">
    <!-- Circle 1 -->
    <svg:circle cx="50" cy="50" r="30" fill="red" />
    <!-- Circle 2 -->
    <svg:circle cx="150" cy="50" r="30" fill="green" />
    <svg:g id="g1"></svg:g>
    <svg:g id="g2"> </svg:g>tail1
    <svg:g id="g3">text1<rect id="rect1"/>text2</svg:g>tail2
</svg:svg>
"""
# remove all newlines/white space at the top level to avoid issues if this file is auto-formated
XML = re.sub(r"[ \t]*\n[ \t]*", "", XML)

NAMESPACES = {"svg": "http://www.w3.org/2000/svg"}


class TestUpdate(unittest.TestCase):

    def test_update_attributes(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        state.update(update(xpath="//svg:svg/svg:circle", attrs={"cx": "10"}))
        result = state.xpath("//svg:svg/svg:circle/@cx")
        self.assertListEqual(result, ["10", "10"])

    def test_update_error(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        with self.assertRaises(XMLQueryError):
            state.update(update(xpath="//svg:svg", attrs={"@tag": "new"}))
        with self.assertRaises(XMLQueryError):
            state.update(update(xpath="//svg:svg", attrs={"@tag": "new"}))
        with self.assertRaises(XMLQueryError):
            state.update(update(xpath="count(//svg:svg/svg:g)", attrs={"a": 1}))
        with self.assertRaises(XMLQueryError):
            state.update(update(xpath="//svg:svg/text()", attrs={"a": 1}))
        with self.assertRaises(XMLQueryError):
            state.update(update(xpath="name(//svg:svg)", attrs={"a": 1}))

    def test_update_text_attribute(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        state.update(update(xpath="//svg:svg/svg:g", attrs={"@text": "new"}))
        text = state.xpath("//svg:svg/svg:g[@id='g2']/text()")
        self.assertListEqual(text, ["new"])  # empty
        text = state.xpath("//svg:svg/svg:g[@id='g1']/text()")
        self.assertListEqual(text, ["new"])  # empty

    def test_update_tail(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        state.update(update(xpath="//svg:svg/svg:g", attrs={"@tail": "new"}))
        text = state.xpath("//svg:svg/text()")
        # NOTE: this is setting the tail for all g, including the g1 which initially is without a tail!
        self.assertListEqual(text, ["new", "new", "new"])  # empty


class TestInsert(unittest.TestCase):

    def test_insert_element_(self):
        # insert element
        ELEMENT = """<svg:circle xmlns:svg="http://www.w3.org/2000/svg" cx="120" cy="60" r="10" fill="blue"/>"""
        state = XMLState(XML, namespaces=NAMESPACES)
        state.insert(insert(xpath="//svg:svg", element=ELEMENT, index=1))
        elements = state.xpath("//svg:svg/svg:circle")
        self.assertEqual(len(elements), 3)
        self.assertEqual(elements[1].get("fill"), "blue")

        # insert element with child
        ELEMENT = """<svg:svg xmlns:svg="http://www.w3.org/2000/svg"> <svg:circle/> </svg:svg>"""
        state = XMLState(XML, namespaces=NAMESPACES)
        state.insert(insert(xpath="//svg:svg", element=ELEMENT, index=1))
        elements = state.xpath("//svg:svg/svg:svg/svg:circle")
        self.assertEqual(len(elements), 1)

    def test_insert_text(self):
        ELEMENT = "some text"
        state = XMLState(XML, namespaces=NAMESPACES)
        state.insert(insert(xpath="//svg:svg", element=ELEMENT, index=2))
        elements = state.xpath("//svg:svg/node()")
        self.assertEqual(elements[2], ELEMENT)

        state.insert(insert(xpath="//svg:svg", element=ELEMENT, index=0))
        elements = state.xpath("//svg:svg/node()")
        self.assertEqual(elements[0], ELEMENT)


class TestDelete(unittest.TestCase):

    def test_delete_element(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        state.delete(delete(xpath="//svg:svg/svg:circle[@fill='green']"))
        elements = state.xpath("//svg:svg/svg:circle")
        self.assertEqual(elements[0].get("fill"), "red")

    def test_delete_attribute(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        state.delete(delete(xpath="//svg:svg/svg:circle[@fill='green']/@cx"))
        elements = state.xpath("//svg:svg/svg:circle[@fill='green']")
        self.assertNotIn("cx", elements[0].get_attributes().keys())

    def test_delete_text_attribute(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        text = state.xpath("//svg:svg/svg:g[@id='g2']/text()")
        self.assertListEqual(text, [" "])
        state.delete(delete(xpath="//svg:svg/svg:g[@id='g2']/text()"))
        text = state.xpath("//svg:svg/svg:g[@id='g2']/text()")
        self.assertFalse(text)  # empty

    def test_delete_error(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        with self.assertRaises(XMLQueryError):
            state.delete(delete(xpath="//svg:svg/svg:circle"))
        with self.assertRaises(XMLQueryError):
            state.delete(delete(xpath="count(//svg:svg/svg:g)"))
        with self.assertRaises(XMLQueryError):
            state.delete(delete(xpath="//svg:svg/text()"))
        with self.assertRaises(XMLQueryError):
            state.delete(delete(xpath="name(//svg:svg)"))


class TestSelect(unittest.TestCase):

    def test_select_text(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        result1 = state.select(select(xpath="//svg:svg/svg:g[@id='g1']/text()"))
        result2 = state.select(
            select(xpath="//svg:svg/svg:g[@id='g1']", attrs=["@text"])
        )
        self.assertEqual(len(result1), 0)
        self.assertIsNone(result2[0]["@text"])
        result1 = state.select(select(xpath="//svg:svg/svg:g[@id='g2']/text()"))
        result2 = state.select(
            select(xpath="//svg:svg/svg:g[@id='g2']", attrs=["@text"])
        )
        self.assertEqual(result1[0], result2[0]["@text"])

    def test_select(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        result = state.select(select(xpath="count(//svg:svg/svg:g)"))
        self.assertListEqual(result, [3])

    def test_select_tail(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        result1 = state.select(
            select(xpath="//svg:svg/svg:g[@id='g3']", attrs=["@tail"])
        )
        result2 = state.select(select(xpath="//svg:svg/text()"))
        self.assertEqual(result1[0]["@tail"], result2[-1])

    def test_select_name(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        result1 = state.select(select(xpath="name(//svg:svg/svg:g[@id='g1'])"))
        result2 = state.select(
            select(xpath="//svg:svg/svg:g[@id='g1']", attrs=["@name"])
        )
        self.assertListEqual(result1, [result2[0]["@name"]])

    def test_select_prefix(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        result = state.select(
            select(xpath="//svg:svg/svg:g[@id='g1']", attrs=["@prefix"])
        )
        self.assertEqual(result[0]["@prefix"], "svg")

    def test_select_attributes(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        result1 = state.select(select(xpath="//svg:svg/svg:circle[@fill='green']/@cx"))
        result2 = state.select(
            select(xpath="//svg:svg/svg:circle[@fill='green']", attrs=["cx"])
        )
        self.assertEqual(result1[0], result2[0]["cx"])

        result1 = state.select(select(xpath="//svg:svg/svg:circle/@cx"))
        result2 = state.select(select(xpath="//svg:svg/svg:circle", attrs=["cx"]))
        self.assertEqual(int(result1[0]), result2[0]["cx"])
        self.assertEqual(int(result1[1]), result2[1]["cx"])

    def test_select_element(self):
        state = XMLState(XML, namespaces=NAMESPACES)
        result = state.select(select(xpath="//svg:svg/svg:circle[@fill='green']"))
        self.assertEqual(
            result[0],
            """<svg:circle xmlns:svg="http://www.w3.org/2000/svg" cx="150" cy="50" fill="green" r="30"></svg:circle>""",
        )


if __name__ == "__main__":
    unittest.main()
