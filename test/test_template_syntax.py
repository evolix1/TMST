import pathlib
import unittest

import fix_import
import tmst.syntax


class Cases:
    all = ("empty_template"
           " one_tag"
           " tag_name_is_followed_by_space"
           " attribute_is_followed_by_space"
           " blank_template"
           " attribute_idly"
           " attribute_can_be_both_captured_and_have_value"
           " attribute_can_be_captured"
           " attribute_can_have_value"
           " attribute_can_have_value_with_simple_quote_also"
           " attribute_value_can_be_empty"
           " autoclosing_tag_doesnt_have_space_at_the_end"
           " attribute_capture_cannot_have_space_before_name"
           " attribute_capture_must_follow_attribute_id"
           " attribute_value_must_follow_attribute_id"
           " attribute_value_when_capture_must_follow_capture"
           " attribute_id_can_only_start_with_letter_not_hypen"
           " attribute_id_can_only_start_with_letter_not_underscore"
           " attribute_id_can_only_start_with_letter_not_number"
           " attribute_id_can_only_start_with_letter_not_colon"
           " attribute_id_has_lowercase_letter"
           " attribute_id_has_uppercase_letter"
           " attribute_id_supports_hypen_and_underscore"
           " tag_name_can_only_start_with_letter_not_hypen"
           " tag_name_can_only_start_with_letter_not_underscore"
           " tag_name_can_only_start_with_letter_not_number"
           " tag_name_can_only_start_with_letter_not_colon"
           " tag_name_has_lowercase_letter"
           " tag_name_has_uppercase_letter"
           " tag_name_supports_hypen_and_underscore"
           "").split()

    def __init__(self):
        self.casedir = pathlib.Path(__file__).resolve().parent / "cases"

    def feed(self, tt):
        for name, func in self.build_tests():
            setattr(tt, name, func)

    def build_tests(self):
        for rawname in Cases.all:
            name = "test_{}".format(rawname)
            yield name, self.hook(rawname)

    def hook(self, rawname):
        success = self.casedir / "{}.success".format(rawname)
        if success.exists():
            return self.hook_success(success)

        error = self.casedir / "{}.error".format(rawname)
        exception = self.casedir / "{}.exception".format(rawname)
        if error.exists() and exception.exists():
            return self.hook_error(error, exception)

        raise RuntimeError("no such test {}".format(rawname))

    def hook_success(self, path):
        with open(path, "r") as case:
            return ValidTest(case.read()).attachment()

    def hook_error(self, path, excpath):
        with open(path, "r") as case:
            with open(excpath, "r") as expected:
                excname, pos, msg = expected.readlines()

            return ErroneousTest(case.read(),
                                 excname.strip(), pos.strip(),
                                 msg.strip()).attachment()


class ValidTest:
    def __init__(self, template):
        self.template = template

    def check_with(self, testcase):
        try:
            tmst.syntax.compile(self.template)
        except Exception as exc:
            testcase.fail(str(exc))

    def attachment(self):
        return lambda x: self.check_with(x)


class ErroneousTest:
    def __init__(self, template, excname, pos, errmsg):
        self.template = template
        assert excname == "PatternSyntaxError", (
            "only PatternSyntaxError is supported")
        self.pos = pos
        self.error_msg = errmsg

    def check_with(self, testcase):
        try:
            tmst.syntax.compile(self.template)
            testcase.fail("expected to raise at {}: {}"
                          .format(self.pos, self.error_msg))
        except tmst.syntax.PatternSyntaxError as exc:
            testcase.assertEqual(exc.pos, self.pos)
            testcase.assertEqual(str(exc), self.error_msg)

    def attachment(self):
        return lambda x: self.check_with(x)


class TestTemplate(unittest.TestCase):
    pass


Cases().feed(TestTemplate)

if __name__ == "__main__":
    unittest.main()
