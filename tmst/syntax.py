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
                "Read at {}: {} ({})".format(self.strpos, self.curr, (
                    "was frozen" if self.frozen_curr else "next")))

            self.frozen_curr = False
            return self.curr

        except StopIteration:
            self.curr = None
            self.stream = None
            raise StopIteration()

    def next(self) -> str:
        try:
            return self.__next__()
        except StopIteration:
            pass

    def freeze_once(self):
        self.frozen_curr = True

    @property
    def strpos(self) -> str:
        return "{row}:{col}".format(row=self.line, col=self.column)


class PatternSyntaxError(RuntimeError):
    def __init__(self, *msg, pos=None, **kw):
        super(PatternSyntaxError, self).__init__(*msg, **kw)
        self.pos = pos


class Reader:
    def __init__(self, source: Source):
        self.source = source

    def raise_error(self, msg):
        # cannot call 'str.format' because it lacks support of bracket escaping
        # like in this """expected '{' with {name}"""
        msg = msg.replace("{curr}", self.source.curr)
        raise PatternSyntaxError(msg, pos=self.source.strpos)

    def skip_ws(self):
        if self.source.done:
            return

        self.source.freeze_once()
        skip = lambda x: x is not None and x.isspace()
        tuple(itertools.takewhile(skip, self.source))

    def match_then_skip_ws(self, context: str):
        if not self.source.curr.isspace():
            self.raise_error("expected whitespace " + context)
        self.source.next()

        self.skip_ws()

    def match(self, sequence, context: str=""):
        assert len(sequence) > 0, "cannot match against nothing"

        self.source.freeze_once()
        for (expected, curr) in zip(sequence, self.source):
            if not curr == expected:
                errmsg = "expected '{}'".format(expected)
                errmsg += ((" " + context) if context else "")
                self.raise_error(errmsg)

        self.source.next()

    def next_identifier(self):
        if not self.source.curr.isalpha():
            return ""

        def valid(t: str):
            return t.isalpha() or t in "-_"

        start = self.source.curr
        return start + "".join(itertools.takewhile(valid, self.source))

    def next_string(self, context: str):
        portal = self.source.curr
        if portal not in ("'", '"'):
            self.raise_error("""expected ''' or '"' """ + context)

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
            if not name:
                reader.raise_error("expected tag name, not '{curr}'")
        reader.match_then_skip_ws("after tag name")

        # pass attributes
        attributes = []
        while source.curr not in (">", "/"):
            attr_name = reader.next_identifier()

            # no identifier found
            if not attr_name:
                # special case if this is after an attribute declaration
                if attributes:
                    last_attr = attributes[-1]
                    # this might an error like this "id :{name}"
                    # or like this "id ='...'"
                    # where the space is misleading
                    # so we did had an identifier but not linked
                    # to the captured name or the attribute value
                    if source.curr == ':':
                        reader.raise_error("unexpected whitespace between"
                                           " attribute and capture")
                    elif source.curr == '=' and not last_attr["capture"]:
                        reader.raise_error("unexpected whitespace between"
                                           " attribute and its value")
                    elif source.curr == '=':
                        reader.raise_error("unexpected whitespace between"
                                           " capture and value")

                reader.raise_error("expected attribute id, not '{curr}'")

            has_capture = (source.curr == ":")
            attr_capture = None
            if has_capture:
                source.next()
                reader.match('{', context="and not '{curr}' to capture attribute")
                attr_capture = reader.next_identifier()
                reader.match('}')

            has_value = (source.curr == '=')
            attr_value = None
            if has_value:
                source.next()
                attr_value = reader.next_string("for attribute value")

            reader.match_then_skip_ws("after attribute")

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
            reader.match(">", context="after '/'")

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
