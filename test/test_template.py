
import unittest

import fix_import
import tmst.syntax


class TestTemplate(unittest.TestCase):

    def test_as_no_template(self):
        expr = tmst.syntax.compile("""""")
        input_page = "<html></html>"
        result = tuple(expr.parse_raw(input_page))
        expected = ()
        self.assertTupleEqual(result, expected)

    def test_cannot_find_any(self):
        expr = tmst.syntax.compile("""<# id='1' class:{classes}></>""")
        input_page = "<html></html>"
        result = tuple(expr.parse_raw(input_page))
        expected = ()
        self.assertTupleEqual(result, expected)

    def test_can_capture_attribute_on_any_tag(self):
        expr = tmst.syntax.compile("""<# id='1' class:{classes} />""")
        input_page = ("<html><body>"
                      "<img id='1' class='target' />"
                      "</body></html>")
        result = expr.parse_raw(input_page)
        expected = (
            { "classes": "target" },
        )
        self.assertTupleEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
