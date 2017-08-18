import pathlib
import unittest

import fix_import
from tmst import syntax


class Cases:
    def __init__(self):
        self.casedir = pathlib.Path(
            __file__).resolve().parent / "template_cases"
        self.test_cases = set()
        self.disabled = set()
        self.avoided = []

    def print_what_did_not_run(self):
        def len_to_bin_index(lg: int):
            return max(0, min(1, lg - 1))

        if self.disabled:
            msg = (
                "There is one test disabled on purpose.",
                "There are {} files test disabled on purpose."
                .format(len(self.disabled)))[len_to_bin_index(len(self.disabled))]

            print()
            print(" ---", msg, "---")
            print()

        if self.avoided:
            if not self.disabled:
                print()

            msg = (
                "THERE IS ONE FILE AVOIDED WITHOUT REASON.",
                "THERE ARE {} FILES AVOIDED WITHOUT REASON."
                .format(len(self.avoided)))[len_to_bin_index(len(self.avoided))]

            print(" ***", msg, "***")
            print()
            print("File(s):", ", ".join(self.avoided))

    def discover_local_tests(self):
        """Register all available test cases from the 'template_cases' folder."""

        def cleaned(path):
            return path.with_suffix("")

        def is_test(path):
            return path.suffix in (".success", ".error", ".exception",
                                   ".fast_err")

        cave = [self.casedir]
        while cave:
            folder = cave.pop(0)
            for entry in folder.iterdir():
                if entry.is_dir():
                    cave.append(entry)
                elif is_test(entry):
                    entry = cleaned(entry)
                    if "disabled" in entry.parts:
                        self.disabled.add(entry)
                    else:
                        self.test_cases.add(entry)
                else:
                    self.avoided.append(entry.name)

    def feed(self, test_class: unittest.TestCase):
        """Inject test case method into the testing class."""
        for name, func in self.build_tests():
            setattr(test_class, name, func)

    def build_tests(self):
        """Build the test case method from registered test cases."""
        for path in self.test_cases:
            name = "test_{}".format(path.name)
            yield name, self.hook(path)

    def hook(self, path: pathlib.Path):
        """Build a test method for the given test case."""
        success = path.with_suffix(".success")
        if success.exists():
            return self.hook_success(success)

        fast_err = path.with_suffix(".fast_err")
        if fast_err.exists():
            return self.hook_fast_error(fast_err)

        error = path.with_suffix(".error")
        exception = path.with_suffix(".exception")
        if error.exists() and exception.exists():
            return self.hook_error(error, exception)

        raise RuntimeError("no such test {}".format(path.name))

    def _bind(self, obj):
        return lambda x: obj.check_with(x)

    def hook_success(self, path: str):
        """Return the test method of the valid test case."""
        with open(path, "r") as case:
            return self._bind(ValidTest(case.read()))

    def hook_error(self, path: str, excpath: str):
        """Return the test method of the invalid test case."""
        with open(path, "r") as case:
            with open(excpath, "r") as expected:
                excname, pos, msg = expected.readlines()

            return self._bind(ErroneousTest(case.read(),
                                 excname.strip(), pos.strip(),
                                 msg.strip()))

    def hook_fast_error(self, path: str):
        """Return the test method of the invalid test case but without
        explanation."""
        with open(path, "r") as case:
            return self._bind(DevErrorTest(case.read(),
                                 excname.strip(), pos.strip(),
                                 msg.strip()))


class ValidTest:
    def __init__(self, template):
        self.template = template

    def check_with(self, testcase):
        try:
            tuple(syntax.compile(self.template))
        except Exception as exc:
            testcase.fail(str(exc))


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


class DevErrorTest:
    def __init__(self, template):
        self.template = template

    def check_with(self, testcase):
        try:
            tuple(syntax.compile(self.template))
            testcase.fail("expected to fail")
        except syntax.PatternSyntaxError as exc:
            pass


class TestTemplate(unittest.TestCase):
    pass


cases = Cases()
cases.discover_local_tests()
cases.feed(TestTemplate)

if __name__ == "__main__":
    import atexit
    atexit.register(cases.print_what_did_not_run)

    unittest.main()
