from __future__ import generator_stop
import logging
import itertools
import collections

from tmst import rfc_xml

if "syntax logging":
    formatter = logging.Formatter("[%(filename)s:%(lineno)03s]"
                                  " %(name)s - %(levelname)s - %(message)s")

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    syntax_logger = logging.getLogger("template.syntax")
    syntax_logger.addHandler(handler)

    source_logger = logging.getLogger("template.source")
    source_logger.addHandler(handler)

    import os
    if os.environ.get("DEBUG", False) in (True, "1"):
        syntax_logger.setLevel(logging.DEBUG)
        source_logger.setLevel(logging.DEBUG)

if "build syntax object":
    new = collections.namedtuple
    """Begining of a tag. Ex: '<span '"""
    OpeningOfTag = new("OpeningOfTag", ["name", "anything"])
    """Ending of an auto-closing tag. Exactly '/>'"""
    EndOfAutoclosingTag = new("EndOfAutoclosingTag", ())
    """Ending of a tag. Exactly: '>'"""
    ClosingOfOpenTag = new("ClosingOfOpenTag", ())
    """Full closing tag. Ex: '</span>' or '</>'"""
    EndTag = new("EndTag", ["maybe_name"])
    """Attribute name. Ex: 'class'"""
    AttributeNamePart = new("AttributeNamePart", ["part"])
    """Attribute capture part. Ex: '{returned_var}'"""
    AttributeCapture = new("AttributeCapture", ["path"])
    """Attribute value. Ex: '"card-title"'"""
    AttributeValue = new("AttributeValue", ["value"])
    """Any identifier in tag name, attribute name or capture."""
    Identifier = new("Identifier", ["label"])
    """Path of identifier."""
    IdentifierPath = new("IdentifierPath", ["parts", "is_relative"])


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
        if self.done:
            return

        try:
            if not self.frozen_curr:
                source_logger.debug("fetch next after {}".format(self.strpos))

                self.curr = next(self.stream)
                assert self.curr is not None
                self.column += 1
                if self.curr == '\n':
                    self.line += 1
                    self.column = 0

            source_logger.debug(
                "read at {}: '{}' ({})".format(self.strpos, self.curr, (
                    "was frozen" if self.frozen_curr else "next")))

            self.frozen_curr = False
            return self.curr

        except StopIteration:
            source_logger.debug("end of stream")

            self.curr = None
            self.stream = None
            raise StopIteration()

    def next(self) -> str:
        try:
            return self.__next__()
        except StopIteration:
            pass

    def freeze_once(self):
        source_logger.debug("freezing source")
        self.frozen_curr = True

    @property
    def strpos(self) -> str:
        return "{row}:{col}".format(row=self.line, col=self.column)

    def raise_error(self, msg):
        # cannot call 'str.format' because it lacks support of bracket escaping
        # like in this example: """expected '{' with {name}"""
        msg = msg.replace("{curr}", self.curr_str)
        raise PatternSyntaxError(msg, pos=self.strpos)


class PatternSyntaxError(RuntimeError):
    def __init__(self, *msg, pos=None, **kw):
        super(PatternSyntaxError, self).__init__(*msg, **kw)
        self.pos = pos


class Anchor:
    def __init__(self, name: str, final_state: bool=False):
        self.name = name
        self.is_final_state = final_state
        self.expectations = []
        self.default_action = None

    def in_case(self, cond: callable, action: callable):
        self.expectations.append((cond, action))
        return self

    def match(self, what: str, action: callable):
        match = lambda x, seq=what: x == what
        self.expectations.append((match, action))
        return self

    def default(self, action: callable):
        self.default_action = action
        return self

    def __iter__(self):
        return iter(self.expectations)

    def conform_to(self, what: [str, None]):
        if what is None:
            return
        result = (action for cond, action in self.expectations if cond(what))
        return next(result, None)


class Parser:
    def __init__(self, source: Source):
        self.source = source

        self._initial_state = (Anchor("initial state",
                                      final_state=True).in_case(
                                          str.isspace, self.skip_ws).match(
                                              '<', self.open_tag))

        self._tag_interval = (Anchor("tag interval").in_case(
            str.isspace, self.ws_in_tag_definition).match(
                '/', self.end_autoclose_tag).match('>', self.end_open_tag))

        self._any_attribute = (Anchor("any attribute").match(
            '/', self.end_autoclose_tag).match(
                '>', self.end_open_tag).default(self.attr_name))

        self._post_attribute_name = (Anchor("post attribute name").in_case(
            str.isspace, self.attr_done).match(':', self.attr_capture).match(
                '=', self.attr_value).match('/', self.end_autoclose_tag).match(
                    '>', self.end_open_tag))

        self._post_attribute_capture = (Anchor("post attribute capture")
                                        .in_case(str.isspace, self.attr_done)
                                        .match('=', self.attr_value).match(
                                            '/', self.end_autoclose_tag).match(
                                                '>', self.end_open_tag))

        self._post_attribute_value = (Anchor("post attribute value").in_case(
            str.isspace, self.attr_done).match('/', self.end_autoclose_tag)
                                      .match('>', self.end_open_tag))

        self.position = self._initial_state

    ###################################
    # Iterator as extraction way

    def __iter__(self):
        return self

    def __next__(self):
        syntax_logger.debug("extract next token from {}"
                            .format(self.position.name))

        token = None
        while token is None:
            token = self.read_one()
        return token

    def read_one(self):
        if not self.source.done:
            self.source.next()

        while True:
            syntax_logger.debug(
                "try to find next action from {}, currently at {} '{}'".format(
                    self.position.name, self.source.strpos, self.source.curr))

            action = self.position.conform_to(self.source.curr)

            if self.source.done:
                syntax_logger.debug("done parsing as source is emptied")
                assert action is None, (
                    "no action expected when no more to read")
                assert self.position.is_final_state, (
                    "current position expected to be final")
                raise StopIteration()

            syntax_logger.debug(
                "action to be called is {}".format(action.__qualname__))
            self.source.next()

            value, self.position = action()
            if value:
                return value

        assert False, "unexpected situation (as it should be not possible)"

    ###################################
    # Parse error

    def raise_unexpected(self, what: str, context: str):
        self.source.raise_error("expected {w} {c}, not '{{curr}}'"
                                .format(w=what, c=context))

    def expect_or_raise_error(self, what: str, context: str):
        if not self.source.curr == what:
            self.raise_unexpected("'" + what + "'", context)
        self.source.next()

    ###################################
    # Extraction utils

    def next_identifier(self, subject: str):
        syntax_logger.debug("extract identifier")

        start = self.source.curr
        if not rfc_xml.char_is_namestart(start):
            self.raise_unexpected("start of name", context="for " + subject)

        name = start + "".join(
            itertools.takewhile(rfc_xml.char_is_name, self.source))
        return Identifier(name)

    def next_identifier_path(self, context: str):
        syntax_logger.debug("extract path of identifiers")

        ident = IdentifierPath(parts=[], is_relative=False)

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
                    self.source.raise_error(
                        "invalid capture identifier with \"{}\""
                        .format(".".join((x.name for x in ident.parts))))

        return ident

    def next_string(self, context: str):
        syntax_logger.debug("extract string")

        portal = self.source.curr
        if portal not in ("'", '"'):
            self.raise_unexpected("""'\'' or '"'""", context)

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

        return value

    ###################################
    # Parse utils

    def skip_ws(self):
        syntax_logger.debug("skip whitespace")

        if not self.source.done:
            self.source.freeze_once()
            skip = lambda x: x is not None and x.isspace()
            tuple(itertools.takewhile(skip, self.source))

        return None, self.position

    def followed_by_whitespace(self, context: str):
        if not self.source.next().isspace():
            self.raise_unexpected("whitespace", context)

    ###################################
    # Open tag parsing

    def open_tag(self):
        syntax_logger.debug("parse tag name")

        if self.source.curr == "#":
            tag = OpeningOfTag(name=None, anything=True)
        else:
            id = self.next_identifier("tag name")
            tag = OpeningOfTag(name=id, anything=False)

        return tag, self._tag_interval

    def ws_in_tag_definition(self):
        syntax_logger.debug("skip whitespace in open tag")

        self.skip_ws()
        return None, self._any_attribute

    def end_autoclose_tag(self):
        syntax_logger.debug("close autocloning tag")

        self.expect_or_raise_error('>', context="after '/'")
        return EndOfAutoclosingTag(), self._initial_state

    def end_open_tag(self):
        syntax_logger.debug("close open tag")

        return ClosingOfOpenTag(), self._initial_state

    ###################################
    # Attribute parsing

    def attr_name(self):
        syntax_logger.debug("parsing attribute name")
        id = self.next_identifier("attribute identifier")

        attr = AttributeName(name=id)
        return name, self._post_attribute_name

    def attr_capture(self):
        syntax_logger.debug("parsing attribute capture")

        self.expect_or_raise_error('{', context="after ':'")
        id = self.next_identifier_path("capture identifier")
        self.expect_or_raise_error('}', context="after capture identifier")

        return AttributeCapture(path=id), self._post_attribute_capture

    def attr_value(self):
        syntax_logger.debug("parsing attribute value")

        v = self.next_string("attribute value")

        return AttributeValue(value=v), self._post_attribute_value

    def attr_done(self):
        syntax_logger.debug("done parsing attribute")
        return None, self._tag_interval


def compile(input: str):
    syntax_logger.info("compile template")

    source = Source(input)
    yield from Parser(source)
