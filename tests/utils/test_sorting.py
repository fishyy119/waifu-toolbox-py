from waifu_toolbox.gui.utils.sorting import localized_sort_key


def test_chinese_names_use_icu_collation() -> None:
    names = ["张三", "阿明", "李四"]

    assert sorted(names, key=lambda value: localized_sort_key(value, "zh_CN")) == [
        "阿明",
        "李四",
        "张三",
    ]


def test_numeric_collation_orders_directory_numbers_naturally() -> None:
    names = ["目录10", "目录2", "目录1"]

    assert sorted(names, key=lambda value: localized_sort_key(value, "zh_CN")) == [
        "目录1",
        "目录2",
        "目录10",
    ]


def test_uppercase_letters_sort_before_lowercase_letters() -> None:
    names = ["alice", "Alice", "bob", "Bob"]

    assert sorted(names, key=lambda value: localized_sort_key(value, "en_US")) == [
        "Alice",
        "alice",
        "Bob",
        "bob",
    ]


def test_mixed_scripts_are_sorted_by_group() -> None:
    names = ["AAA", "aaa", "BBB", ".cool", "CLANNAD", "9-nine-", "张三", "李四"]

    assert sorted(names, key=lambda value: localized_sort_key(value, "zh_CN")) == [
        ".cool",
        "9-nine-",
        "AAA",
        "aaa",
        "BBB",
        "CLANNAD",
        "李四",
        "张三",
    ]
