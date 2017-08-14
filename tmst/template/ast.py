class Identifier:
    def __init__(self, name: str=None):
        self.name = name

    def __str__(self) -> str:
        return self.name if self.name else ""

    def __eq__(self, other) -> bool:
        return self.name == getattr(other, "name", None)

    def __bool__(self) -> bool:
        return self.is_valid()

    def is_valid(self) -> bool:
        return bool(self.name)


class PathOfIdentifier:
    def __init__(self, parts: (Identifier, )=None, absolute=True):
        self.parts = [] if parts is None else list(parts)
        self.is_absolute = absolute

    @property
    def is_relative(self):
        return not self.is_absolute

    @is_relative.setter
    def is_relative(self, value: bool):
        self.is_absolute = not value

    def __str__(self) -> str:
        prefix = "" if self.is_absolute else "."
        return prefix + ".".join(map(str, self.parts))

    def __eq__(self, other) -> bool:
        return (self.is_absolute == getattr(other, "is_absolute", None)
                and self.parts == getattr(other, "parts", None))

    def __bool__(self) -> bool:
        return self.is_valid()

    def is_valid(self) -> bool:
        return bool(self.parts) and all(bool(x) for x in self.parts)


class Attribute:
    def __init__(self,
                 name: Identifier,
                 capture: PathOfIdentifier=None,
                 value: str=None):
        self.name = name
        self.capture = capture
        self.value = value


class OpenTag:
    def __init__(self, name: str):
        self.name = name
        self.attributes = []
