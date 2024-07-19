"""Unit test for serialisation of XML events."""

import unittest
from star_ray_xml import Update, Replace, Insert, Delete, Select, Expr


class TestEventSerialisation(unittest.TestCase):
    """Test XML event serialisation."""

    def test_update(self):
        """Test Update."""
        u1 = Update(
            xpath="test",
            attrs={
                "a": 1,
                "b": Expr("{x1} + {x2}", x1=1),
                "c": "123",
                "d": True,
                "e": 1.0,
            },
        )
        u2 = Update.model_validate_json(u1.model_dump_json())
        self.assertEqual(u1, u2)

    def test_insert(self):
        """Test Insert."""
        u1 = Insert(xpath="test", element="test element", index=0)
        u2 = Insert.model_validate_json(u1.model_dump_json())
        self.assertEqual(u1, u2)

    def test_delete(self):
        """Test Delete."""
        u1 = Delete(xpath="test")
        u2 = Delete.model_validate_json(u1.model_dump_json())
        self.assertEqual(u1, u2)

    def test_replace(self):
        """Test Replace."""
        u1 = Replace(xpath="test", element="test element")
        u2 = Replace.model_validate_json(u1.model_dump_json())
        self.assertEqual(u1, u2)

    def test_select(self):
        """Test Select."""
        u1 = Select(xpath="test", attrs=["x", "y"])
        u2 = Select.model_validate_json(u1.model_dump_json())
        self.assertEqual(u1, u2)


if __name__ == "__main__":
    unittest.main()
