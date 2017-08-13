from __future__ import generator_stop
import itertools

import logging

from tmst import ast


class Source:
    def __init__(self, stream):
        self.line = 0
        self.column = -1
        self.stream = iter(stream)
        self.curr = None
        self.frozen_curr = False

    @property
    def done(self):
        return self.stream is None

    def __iter__(self):
        return self

    def __next__(self) -> str:
        try:
            if not self.frozen_curr:
                self.curr = next(self.stream)
                assert self.curr is not None
                self.column += 1
                if self.curr == '\n':
                    self.line += 1
                    self.column = 0
            logging.root.debug(
                "Read at {}: {} ({})".format(
                    self.context(), 
                    self.curr, 
                    ("was frozen" if self.frozen_curr else "next")))
            self.frozen_curr = False
            return self.curr
        except StopIteration:
            self.curr = None
            self.stream = None
            raise GeneratorExit()

    def next(self) -> str:
        try:
            return self.__next__()
        except GeneratorExit:
            pass

    def freeze_once(self):
        self.frozen_curr = True

    def context(self) -> str:
        return "{row}:{col}".format(row=self.line, col=self.column)


class PatternSyntaxError(RuntimeError):
    pass


class Reader:
    def __init__(self, source: Source):
        self.source = source

    def raise_error(self, msg):
        errmsg = "error at {context}: {msg}".format(
            context=self.source.context(), msg=msg)
        raise PatternSyntaxError(errmsg)

    def skip_ws(self):
        self.source.freeze_once()
        tuple(itertools.takewhile(str.isspace, self.source))

    def match_ws(self):
        if not self.source.curr.isspace():
            self.raise_error("expected whitespace")
        self.source.next()

    def match(self, sequence):
        assert len(sequence) > 0, "cannot match against nothing"

        self.source.freeze_once()
        for (expected, curr) in zip(sequence, self.source):
            if not curr == expected:
                self.raise_error("expected '{}'".format(expected))

        self.source.next()

    def next_identifier(self):
        def valid(t: str):
            return t.isalpha() or t in "-_"

        self.source.freeze_once()
        return "".join(itertools.takewhile(valid, self.source))

    def next_string(self):
        portal = self.source.curr
        if portal not in ("'", '"'):
            self.raise_error("""expected ''' or '"'""")

        escaping = False
        value = ""
        for curr in self.source:
            if curr == portal and not escaping:
                break

            value += curr
            if escaping:
                escaping = False
            elif curr == "\\":
                escaping = True

        self.source.next()
        return value


class Tag:
    @staticmethod
    def parse_begin_tag(source: Source):
        reader = Reader(source)

        # move at the begining af the tag declaratation
        reader.skip_ws()
        reader.match("<")

        # pass the tag name
        name = None
        if source.curr == "#":
            source.next()
        else:
            name = reader.next_identifier()
        reader.match_ws()
        reader.skip_ws()

        # pass attributes
        attributes = []
        while source.curr not in (">", "/"):
            attr_name = reader.next_identifier()

            has_capture = (source.curr == ":")
            attr_capture = None
            if has_capture:
                source.next()
                reader.match("{")
                attr_capture = reader.next_identifier()
                reader.match("}")

            has_value = (source.curr == "=")
            attr_value = None
            if has_value:
                source.next()
                attr_value = reader.next_string()

            reader.match_ws()

            attributes.append({
                "name": attr_name,
                "capture": attr_capture,
                "value": attr_value
            })

            reader.skip_ws()

        # pass tag end
        is_auto_closing = (source.curr == "/")
        if is_auto_closing:
            source.next()
        reader.match(">")

        return {
            "name": name,
            "attrs": attributes,
            "auto_close": is_auto_closing
        }

    @staticmethod
    def build(tag_info: dict) -> ast.Visitor:
        v = ast.Visitor()

        if tag_info["name"] is not None:
            cond = ast.filter_tag_name(tag_info["name"])
            v.identifiers.append(cond)

        for attr_def in tag_info["attrs"]:
            if attr_def["capture"] is not None:
                capt = ast.capture_tag_attr(attr_def["name"],
                                            attr_def["capture"])
                v.captures.append(capt)

            if attr_def["value"] is not None:
                cond = ast.filter_tag_attr(attr_def["name"], attr_def["value"])
                v.identifiers.append(cond)

        return v

    @staticmethod
    def parse_build(source: Source):
        Reader(source).skip_ws()
        while not source.done:
            begin_tag = Tag.parse_begin_tag(source)
            assert begin_tag.get("auto_close", False) is True
            yield Tag.build(begin_tag)

            if not source.done:
                Reader(source).skip_ws()


def compile(input: str):
    logging.root.info("compile template")
    source = Source(input)
    source.next()
    root = ast.Visitor()
    root.children = tuple(Tag.parse_build(source))
    return root
