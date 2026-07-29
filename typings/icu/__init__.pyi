from typing import ClassVar, Self

class Locale:
    def __init__(self, name: str = ...) -> None: ...
    @staticmethod
    def getDefault() -> Locale: ...

class Collator:
    PRIMARY: int
    SECONDARY: int
    TERTIARY: int

    @staticmethod
    def createInstance(locale: Locale = ...) -> Collator: ...
    def getSortKey(self, source: str) -> bytes: ...
    def setStrength(self, strength: int) -> None: ...
    def setAttribute(self, attribute: int, value: int) -> None: ...

class Script:
    code: int

    @classmethod
    def getScript(cls, codepoint: int | str) -> Self: ...

class UCollAttribute:
    NORMALIZATION_MODE: int
    NUMERIC_COLLATION: int
    CASE_FIRST: int

class UCollAttributeValue:
    ON: int
    UPPER_FIRST: int

class UScriptCode:
    LATIN: ClassVar[int]
    HAN: ClassVar[int]
    HIRAGANA: ClassVar[int]
    KATAKANA: ClassVar[int]
    COMMON: ClassVar[int]
