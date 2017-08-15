from __future__ import generator_stop
import itertools

import logging

from . import ast


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

    @property
    def curr_str(self):
        return "" if self.curr is None else self.curr

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
        # like in this example: """expected '{' with {name}"""
        msg = msg.replace("{curr}", self.source.curr_str)
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
            return ast.Identifier()

        def valid(t: str):
            return t.isalpha() or t in "-_"

        start = self.source.curr
        name = start + "".join(itertools.takewhile(valid, self.source))
        return ast.Identifier(name)

    def next_identifier_path(self):
        ident = ast.IdentifierPath()

        if self.source.curr == ".":
            ident.is_relative = True
            self.source.next()

        has_next = True
        while has_next:
            has_next = False
            name = self.next_identifier()
            if name:
                ident.parts.append(name)

                if self.source.curr == ".":
                    self.source.next()
                    has_next = True

            elif ident.parts:
                # special case if this ends with dot
                # like in """root.name."""
                # it appends an invalid identifier
                # so the path of identifier is itself invalid
                ident.parts.append(ast.Identifier())
                assert ident.is_valid() is False, (
                    "action failed to make it invalid")

        return ident

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


class Parser:
    def __init__(self, source: Source):
        self.source = source

    def open_tag(self):
        reader = Reader(self.source)
        otag = ast.OpenTag()

        # move at the begining af the tag declaratation
        reader.match("<")

        # pass the tag name
        if self.source.curr == "#":
            self.source.next()
        else:
            otag.name = reader.next_identifier()
            if not otag.name:
                reader.raise_error("expected tag name, not '{curr}'")
        reader.match_then_skip_ws("after tag name")

        # pass attributes
        while self.source.curr not in (">", "/"):
            attr = ast.Attribute()
            attr.name = reader.next_identifier()

            # no identifier found
            if not attr.name:
                # special case if this is after an attribute declaration
                if otag.attributes:
                    last_attr = otag.attributes[-1]
                    # this might an error like this "id :{name}"
                    # or like this "id ='...'"
                    # where the space is misleading
                    # so we did had an identifier but not linked
                    # to the captured name or the attribute value
                    if self.source.curr == ':':
                        reader.raise_error("unexpected whitespace between"
                                           " attribute identifier"
                                           " and capture identifier")
                    elif self.source.curr == '=' and not last_attr.capture:
                        reader.raise_error(
                            "unexpected whitespace between"
                            " attribute identifier and its value")
                    elif self.source.curr == '=':
                        reader.raise_error("unexpected whitespace between"
                                           " capture identifier"
                                           " and attribute value")

                reader.raise_error(
                    "expected attribute identifier, not '{curr}'")

            has_capture = (self.source.curr == ':')
            if has_capture:
                self.source.next()
                reader.match(
                    '{', context="and not '{curr}' to capture the attribute")
                attr.capture = reader.next_identifier_path()

                # no capture name found
                # (same as empty which is the default state)
                if attr.capture == ast.IdentifierPath():
                    # special case if no name provided
                    if self.source.curr == '}':
                        reader.raise_error("capture must have an identifier")
                    reader.raise_error(
                        "expected capture identifier, not '{curr}'")
                elif not attr.capture.is_valid():
                    reader.raise_error(
                        "invalid capture identifier"
                        " with \"{}\"".format(str(attr.capture)))

                reader.match(
                    '}', context="and not '{curr}' after capture identifier")

            has_value = (self.source.curr == '=')
            if has_value:
                self.source.next()
                attr.value = reader.next_string("for attribute value")

            otag.attributes.append(attr)
            reader.match_then_skip_ws("after attribute")
            reader.skip_ws()

        # pass tag end
        otag.auto_close = (self.source.curr == "/")
        if otag.auto_close:
            self.source.next()
            reader.match(">", context="after '/'")

        assert otag.auto_close, "only autoclosing tag supported"
        reader.skip_ws()

        return otag


def compile(input: str):
    logging.root.info("compile template")

    source = Source(input)
    skip_ws = Reader(source).skip_ws

    # initiate reading
    source.next()
    skip_ws()

    while not source.done:
        yield Parser(source).open_tag()
        skip_ws()
