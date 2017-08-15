
from tmst.parser import toolbox
from tmst.template import syntax, ast


def generate_parser(ast_elements: iter) -> toolbox.Parser:
    root = toolbox.Parser()

    for token in ast_elements:
        assert isinstance(token, ast.OpenTag), "only OpenTag supported"
        assert token.auto_close, "only auto-closing tag supported"

        opentag_parser = toolbox.Parser()

        if token.name:
            cond = toolbox.match_tag_name(str(token.name))
            opentag_parser.filters.append(cond)

        for attr in token.attributes:
            if attr.capture:
                extractor = toolbox.capture_attr(
                    str(attr.name), str(attr.capture))
                opentag_parser.capturing_net.append(extractor)

            if attr.value:
                cond = toolbox.match_attr(str(attr.name), attr.value)
                opentag_parser.filters.append(cond)

        if not opentag_parser.is_empty():
            root.subs.append(opentag_parser)

    return root
