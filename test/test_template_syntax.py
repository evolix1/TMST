import pathlib
import unittest

import fix_import
import tmst.syntax


class Cases:
    all = ("no_template one_tag tag_name_are_followed_by_space"
           " attribute_idly").split()

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
        except tmst.syntax.PatternSyntaxError as exc:
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
