import lxml.html

import logging


class Namespace(dict):
    def __getattr__(self, name):
        sulf = super(Namespace, self)
        return sulf.__getitem__(name)

    def __setattr__(self, name, value):
        sulf = super(Namespace, self)
        sulf.__setitem__(name, value)


def filter_tag_name(x):
    def is_tag_name(dom):
        return dom.tag == x

    return is_tag_name


def filter_tag_attr(name, value):
    def has_class(dom):
        return all(
            v in dom.classes for v in map(str.strip, value.split(" ")) if v)

    def has_tag_attr(dom):
        return dom.attrib.get(name, None) == value

    return (has_class if name == "class" else has_tag_attr)


def capture_tag_attr(name, rename):
    def fetch_class(dom):
        return dom.get("class")

    def fetch_attr(dom):
        return dom.attrib.get(name)

    return (rename, (fetch_class if name == "class" else fetch_attr))


class Visitor:
    def __init__(self):
        self.identifiers = []
        self.captures = []
        self.children = []

        self.owned_data = Namespace()
        self.children_data = []

    def can_be(self, dom: lxml.html.HtmlElement):
        return all(ident(dom) for ident in self.identifiers)

    def parse_raw(self, content: str):
        logging.root.info("parse html for extraction")
        dom = lxml.html.fromstring(content)
        result = self.parse(dom)
        return result.get("_children", ())

    def parse(self, dom: lxml.html.HtmlElement):
        data = Namespace()

        if self.captures:
            data.update(dict(self.take(dom)))

        if self.children:
            data._children = tuple(self.forward(dom))

        return data

    def take(self, dom: lxml.html.HtmlElement) -> (str, str):
        for key, fetcher in self.captures:
            yield key, fetcher(dom)

    def forward(self, dom: lxml.html.HtmlElement):
        stack = []
        stack.extend(dom.getchildren())

        while stack:
            root = stack.pop(0)

            elligible_child = None
            for child in self.children:
                if child.can_be(root):
                    elligible_child = child
                    break

            if elligible_child:
                yield elligible_child.parse(root)
            else:
                stack.extend(root.getchildren())
