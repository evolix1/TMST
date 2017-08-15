import pathlib
import unittest

import fix_import
from tmst.template import syntax


class Cases:
    def __init__(self):
        self.casedir = pathlib.Path(
            __file__).resolve().parent / "template_cases"
        self.test_cases = set()
        self.avoided = []

    def print_ignored_content(self):
        if not self.avoided:
            return

        msg = (
            "THERE IS ONE FILE IGNORED WITHOUT REASON.",
            "THERE ARE {} FILES IGNORED WITHOUT REASON."
            .format(len(self.avoided)))[max(0, min(1, len(self.avoided) - 1))]

        print()
        print(" ***", msg, "***")
        print()
        print("File(s):", ", ".join(self.avoided))

    def discover_local_tests(self):
        """Register all available test cases from the 'template_cases' folder."""

        def clean(path):
            return path.stem

        def is_test(path):
            return path.suffix in (".success", ".error", ".exception")

        for entry in self.casedir.iterdir():
            if is_test(entry):
                self.test_cases.add(clean(entry))
            else:
                self.avoided.append(entry.name)

    def feed(self, test_class: unittest.TestCase):
        """Inject test case method into the testing class."""
        for name, func in self.build_tests():
            setattr(test_class, name, func)

    def build_tests(self):
        """Build the test case method from registered test cases."""
        for rawname in self.test_cases:
            name = "test_{}".format(rawname)
            yield name, self.hook(rawname)

    def hook(self, rawname: str):
        """Build a test method for the given test case."""
        success = self.casedir / "{}.success".format(rawname)
        if success.exists():
            return self.hook_success(success)

        error = self.casedir / "{}.error".format(rawname)
        exception = self.casedir / "{}.exception".format(rawname)
        if error.exists() and exception.exists():
            return self.hook_error(error, exception)

        raise RuntimeError("no such test {}".format(rawname))

    def hook_success(self, path: str):
        """Return the test method of the valid test case."""
        with open(path, "r") as case:
            return ValidTest(case.read()).attachment()

    def hook_error(self, path: str, excpath: str):
        """Return the test method of the invalid test case."""
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
            tuple(syntax.compile(self.template))
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
            tuple(syntax.compile(self.template))
            testcase.fail("expected to raise at {}: {}"
                          .format(self.pos, self.error_msg))
        except syntax.PatternSyntaxError as exc:
            testcase.assertEqual(exc.pos, self.pos)
            testcase.assertEqual(str(exc), self.error_msg)

    def attachment(self):
        return lambda x: self.check_with(x)


class TestTemplate(unittest.TestCase):
    pass


cases = Cases()
cases.discover_local_tests()
cases.feed(TestTemplate)

if __name__ == "__main__":
    import atexit
    atexit.register(cases.print_ignored_content)

    unittest.main()
