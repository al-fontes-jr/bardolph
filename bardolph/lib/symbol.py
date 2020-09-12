from enum import Enum

from ..lib.auto_repl import auto


class SymbolType(Enum):
    EXTERN = auto()
    MACRO = auto()
    NO_TYPE = auto()
    PARAM = auto()
    ROUTINE = auto()
    UNKNOWN = auto()
    VAR = auto()

class Symbol:
    def __init__(self, name, symbol_type=SymbolType.UNKNOWN, value=None):
        self._name = name
        self._symbol_type = symbol_type
        self._value = value

    def __repr__(self):
        return 'Symbol("{}", {}, {})'.format(
            self.name, self.symbol_type, self.value)

    @property
    def name(self):
        return self._name

    @property
    def symbol_type(self):
        return self._symbol_type

    @property
    def value(self):
        return self._value
