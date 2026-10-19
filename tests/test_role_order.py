from src.utils.role_order import role_positions_after_move, target_role_position

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


def test_move_includes_the_moved_role_and_shifts_roles_in_between() -> None:
    # 最新の位置: @everyone(0), 新しいロール(1), p001(2), e001(3), c001(4)
    roles = [(0, 0), (999, 1), (101, 2), (201, 3), (301, 4)]

    # 新しいロールを位置3（c001のすぐ下）へ動かす
    positions = role_positions_after_move(roles, role_id=999, target=3)

    assert positions == {101: 1, 201: 2, 999: 3}


def test_move_is_given_up_when_positions_are_inconsistent() -> None:
    # 位置2が重複している（Discord側で位置が揃っていない）
    roles = [(0, 0), (999, 1), (101, 2), (102, 2), (201, 3)]

    assert role_positions_after_move(roles, role_id=999, target=3) == {}
