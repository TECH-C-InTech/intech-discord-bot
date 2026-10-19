from src.utils.capacity import (
    Capacity,
    check_creation_capacity,
    check_move_capacity,
    remaining_capacity,
)


def test_creation_is_allowed_when_everything_has_room() -> None:
    assert check_creation_capacity(category_channels=10, guild_channels=100, guild_roles=50) is None


def test_creation_is_allowed_when_category_has_49_channels() -> None:
    assert check_creation_capacity(category_channels=49, guild_channels=100, guild_roles=50) is None


def test_creation_is_rejected_when_category_is_full() -> None:
    reason = check_creation_capacity(category_channels=50, guild_channels=100, guild_roles=50)
    assert reason is not None
    assert "カテゴリ" in reason


def test_creation_is_allowed_when_guild_has_499_channels() -> None:
    assert check_creation_capacity(category_channels=10, guild_channels=499, guild_roles=50) is None


def test_creation_is_rejected_when_guild_channels_are_full() -> None:
    reason = check_creation_capacity(category_channels=10, guild_channels=500, guild_roles=50)
    assert reason is not None
    assert "サーバーのチャンネル" in reason


def test_creation_is_allowed_when_guild_has_249_roles() -> None:
    assert (
        check_creation_capacity(category_channels=10, guild_channels=100, guild_roles=249) is None
    )


def test_creation_is_rejected_when_roles_are_full() -> None:
    reason = check_creation_capacity(category_channels=10, guild_channels=100, guild_roles=250)
    assert reason is not None
    assert "ロール" in reason


def test_move_is_allowed_when_destination_has_49_channels() -> None:
    assert check_move_capacity(destination_category_channels=49) is None


def test_move_is_rejected_when_destination_is_full() -> None:
    reason = check_move_capacity(destination_category_channels=50)
    assert reason is not None
    assert "移動先" in reason


def test_remaining_capacity_is_limit_minus_current_count() -> None:
    assert remaining_capacity(category_channels=12, guild_channels=179, guild_roles=80) == Capacity(
        category_channels=38, guild_channels=321, guild_roles=170
    )
