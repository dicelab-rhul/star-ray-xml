import unittest
from star_ray_xml import Expr


class TestExpr(unittest.TestCase):

    def test_init(self):
        expr = "2 * {value}"
        expr_obj = Expr(expr)
        self.assertEqual(expr_obj.expr, "2 * {value}")

    def test_eval(self):
        expr = "2 * {value}"
        expr_obj = Expr(expr)
        result = expr_obj.eval(None, 5)
        self.assertEqual(result, 10)

    def test_init_missing_key(self):
        expr = "2 * {missing_key}"
        with self.assertRaises(KeyError):
            Expr(expr, x=1)

    def test_eval_with_list(self):
        expr = "{other} + {value}"
        expr_obj = Expr(expr, other=[2, 3, 4])
        print(expr_obj.expr)
        result = expr_obj.eval(None, [3, 5, 10, 2])
        self.assertEqual(result, [2, 3, 4, 3, 5, 10, 2])


if __name__ == "__main__":
    unittest.main()
