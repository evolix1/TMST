import pathlib
import unittest
import lxml.html
import json

import fix_import
import tmst


class Cases:
    def __init__(self):
        self.casedir = pathlib.Path(
            __file__).resolve().parent / "capture_cases"
        self.test_cases = set()
        self.avoided = []
        self.cache = {}

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

        def is_legal(path):
            return path.suffix in (".template", ".html")

        def is_test(path):
            return path.suffix == ".result"

        for entry in self.casedir.iterdir():
            if is_test(entry):
                self.test_cases.add(clean(entry))
            elif not is_legal(entry):
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
        result = self.casedir / "{}.result".format(rawname)
        if result.exists():
            with open(result, "r") as case:
                # both template and data line are like this "xxx:value"
                template_filename = (case.readline().strip()
                                     .replace("template:", ""))
                data_filename = (case.readline().strip()
                                 .replace("data:", ""))

                template = self.load(template_filename + ".template")
                input_data = self.load(data_filename + ".html")
                result_data = case.read()

                return CaptureCase(template, input_data,
                                      result_data).attachment()

        raise RuntimeError("no such test {}".format(rawname))

    def load(self, filename: str):
        """Load file from disk and cache it to later reloading."""
        cached = self.cache.get(filename, None)
        if cached is None:
            with open(str(self.casedir / filename), "r") as ifile:
                cached = ifile.read()
            self.cache[filename] = cached
        return cached


class CaptureCase:
    def __init__(self, template, input_data, result):
        self.template = template
        self.input_data = input_data
        self.expected_result = json.loads(result)

    def check_with(self, testcase):
        parser = tmst.compile(self.template)
        input_dom = lxml.html.fromstring(self.input_data)
        result = parser.capture_from(input_dom)

        testcase.assertEqual(result, self.expected_result)

    def attachment(self):
        return lambda x: self.check_with(x)


class TestCapture(unittest.TestCase):
    pass


cases = Cases()
cases.discover_local_tests()
cases.feed(TestCapture)

if __name__ == "__main__":
    import atexit
    atexit.register(cases.print_ignored_content)

    unittest.main()
