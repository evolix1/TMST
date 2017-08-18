# Source:
# https://www.w3.org/TR/REC-xml/


def char_is_whitespace(w: str):
    """Return true if it is match 's' definition [3]."""
    return w.isspace()


def char_is_namestart(w: str):
    """Return true if it is match 'NameStartChar' definition [4]."""
    return w.isalpha() or w in ":_"


def char_is_name(w: str):
    """Return true if it is match 'NameChar' definition [4a]."""
    return char_is_namestart(w) or w.isdigit() or w in "-."
