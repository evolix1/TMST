import lxml.html

from tmst.template import ast


class match_tag_name:
    def __init__(self, name: ast.Identifier):
        self.name = str(name)

    def __call__(self, dom: lxml.html.HtmlElement) -> bool:
        return dom.tag == self.name


def match_attr(name: ast.Identifier, value: ast.IdentifierPath):
    class_ = MatchClassAttribute if str(name) == "class" else MatchPlainAttribute
    return class_(name, value)


class MatchPlainAttribute:
    def __init__(self, name: ast.Identifier, value: str):
        self.name = str(name)
        self.value = value
        assert bool(self.value), ("nothing to match for \"{}\" attribute"
                                  .format(self.name))

    def __call__(self, dom: lxml.html.HtmlElement) -> bool:
        return dom.attrib.get(self.name, None) == self.value


class MatchClassAttribute:
    def __init__(self, _, rawclasses: str):
        self.classes = tuple(x.strip() for x in rawclasses.split())
        assert bool(self.classes), "nothing to match for \"class\" attribute"

    def __call__(self, dom: lxml.html.HtmlElement) -> bool:
        return all(x in dom.classes for x in self.classes)


class capture_attr:
    def __init__(self, name: ast.Identifier, capture_name: ast.IdentifierPath):
        self.name = str(name)
        self.hook = (self.fetch_class if self.name == "class" else self.fetch_any)
        self.capture_name = capture_name

    def fetch_class(self, dom):
        return dom.get("class")

    def fetch_any(self, dom):
        return dom.attrib.get(self.name)

    def __call__(self, dom: lxml.html.HtmlElement, storage: dict):
        val_storage = storage.get(str(self.capture_name), [])
        val_storage.append(self.hook(dom))
        storage[str(self.capture_name)] = val_storage


class Parser:
    def __init__(self):
        self._is_root = False
        self.filters = []
        self.capturing_net = []
        self.subs = []

    def has_subs(self) -> bool:
        return bool(self.subs)

    def is_empty(self) -> bool:
        return not bool(self.filters) and not bool(self.capturing_net)

    def match(self, dom: lxml.html.HtmlElement) -> bool:
        return not bool(self.filters) or all(f(dom) for f in self.filters)

    def capture(self, dom: lxml.html.HtmlElement, storage: dict):
        for tool in self.capturing_net:
            tool(dom, storage)

    def capture_from(self, dom: lxml.html.HtmlElement):
        data = {}
        self._dig(dom, storage=data)
        return data

    def _dig(self, dom: lxml.html.HtmlElement, storage: dict):
        stack = []
        stack.extend(dom.getchildren())

        while stack:
            root = stack.pop(0)

            subtree_read = False
            for child in self.subs:
                if child.match(root):
                    child.capture(root, storage)
                    if child.has_subs():
                        child._dig(root, storage)

            if not subtree_read:
                stack.extend(root.getchildren())
