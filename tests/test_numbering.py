from src.utils.numbering import next_number, number_of, with_number


def test_first_number_is_one() -> None:
    assert next_number("c", ["雑談", "e001-x"]) == 1


def test_next_number_follows_the_largest_without_filling_gaps() -> None:
    assert next_number("c", ["c001-ラーメン", "c003-ボドゲ", "c002-映画"]) == 4


def test_other_kinds_and_unnumbered_names_are_not_counted() -> None:
    assert next_number("c", ["e009-x", "p007", "ラーメン", "c002-映画"]) == 3


def test_number_is_read_from_numbered_name() -> None:
    assert number_of("c", "c005-ラーメン") == 5


def test_unnumbered_or_other_kind_name_has_no_number() -> None:
    assert number_of("c", "ラーメン") is None
    assert number_of("c", "e005-x") is None


def test_items_with_the_number_are_picked_by_name() -> None:
    names = ["c003-映画", "c004-写真", "c003-写真", "e003"]

    assert with_number("c", 3, names, name=lambda n: n) == ["c003-映画", "c003-写真"]
