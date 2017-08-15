from tmst import mimetic
from tmst.parser import toolbox
from tmst.template import syntax


def compile(source: str) -> toolbox.Parser:
    return mimetic.generate_parser(syntax.compile(source))
