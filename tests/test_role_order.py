from src.utils.role_order import target_role_position

# (ロール名, 位置)。位置は大きいほど上
ROLES = [
    ("管理者", 20),
    ("InTech Bot", 19),
    ("分野", 18),
    ("c001-ラーメン", 17),
    ("c002-映画", 16),
    ("e001", 15),
    ("e002", 14),
    ("p001", 13),
    ("@everyone", 0),
]


def test_new_role_goes_just_below_the_lowest_role_of_its_kind() -> None:
    # 新しいロールは一番下（位置1）にある。c002-映画（16）のすぐ下に入れるには16-1に動かす
    assert target_role_position("club", ROLES) == 15


def test_first_role_of_its_kind_goes_just_above_lower_kinds() -> None:
    roles = [(name, pos) for name, pos in ROLES if not name.startswith("e")]

    # eventのロールがない。projectで一番上のp001（13）のすぐ上に入れるには13に動かす
    assert target_role_position("event", roles) == 13


def test_role_stays_at_bottom_when_no_same_or_lower_kind_exists() -> None:
    roles = [("管理者", 3), ("分野", 2), ("c001-ラーメン", 1)]

    assert target_role_position("project", roles) is None


def test_kinds_are_told_apart_by_role_name_format() -> None:
    # 「e001-なにか」はeventのロールではない（eventのロールは番号だけ）
    roles = [("c001-ラーメン", 5), ("e001-なにか", 4), ("p001", 3)]

    assert target_role_position("event", roles) == 3
