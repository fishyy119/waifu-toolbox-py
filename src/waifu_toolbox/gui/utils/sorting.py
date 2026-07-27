from functools import lru_cache

from icu import (
    Collator,
    Locale,
    Script,
    UCollAttribute,
    UCollAttributeValue,
    UScriptCode,
)


@lru_cache(maxsize=None)
def _get_collator(locale_name: str | None = None) -> Collator:
    locale = Locale(locale_name) if locale_name is not None else Locale.getDefault()
    collator = Collator.createInstance(locale)

    collator.setStrength(Collator.TERTIARY)
    collator.setAttribute(UCollAttribute.NORMALIZATION_MODE, UCollAttributeValue.ON)
    collator.setAttribute(UCollAttribute.NUMERIC_COLLATION, UCollAttributeValue.ON)
    collator.setAttribute(UCollAttribute.CASE_FIRST, UCollAttributeValue.UPPER_FIRST)

    return collator


_GROUP_MAP = {
    UScriptCode.COMMON: 0,
    UScriptCode.LATIN: 1,
    UScriptCode.HAN: 2,
}
_OTHER_GROUP = 3


def _sort_group(value: str) -> int:
    if not value:
        return _OTHER_GROUP

    return _GROUP_MAP.get(
        Script.getScript(value[0]).code,
        _OTHER_GROUP,
    )


def localized_sort_key(value: str, locale_name: str | None = None) -> tuple[int, bytes, str]:
    return (
        _sort_group(value),
        bytes(_get_collator(locale_name).getSortKey(value)),
        value,
    )
