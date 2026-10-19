from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.channel_order import move_channel, sort_category, sorted_channel_positions
from src.utils.kinds import CLUB


def test_numbered_channels_are_ordered_by_number() -> None:
    # (ID, 名前, 位置)。e017がe001より上に入ってしまっている
    channels = [(17, "e017-x", 10), (1, "e001-a", 11), (5, "e005-b", 12)]

    assert sorted_channel_positions("e", channels) == {1: 10, 5: 11, 17: 12}


def test_unnumbered_channels_stay_on_top_in_their_current_order() -> None:
    channels = [(1, "e002-a", 3), (2, "案内", 4), (3, "雑談", 5), (4, "e001-b", 6)]

    assert sorted_channel_positions("e", channels) == {2: 3, 3: 4, 4: 5, 1: 6}


def test_nothing_is_sent_when_already_sorted() -> None:
    channels = [(1, "e001-a", 3), (2, "e002-b", 4)]

    assert sorted_channel_positions("e", channels) == {}


def test_duplicate_positions_become_unique() -> None:
    # 移動してきたチャンネルが既存のチャンネルと同じ位置になっている
    channels = [(1, "e001-a", 3), (2, "e002-b", 4), (3, "e003-c", 4)]

    assert sorted_channel_positions("e", channels) == {3: 5}


def test_other_kinds_of_numbers_are_treated_as_unnumbered() -> None:
    channels = [(1, "e001-a", 3), (2, "p001-x", 4)]

    assert sorted_channel_positions("e", channels) == {2: 3, 1: 4}


def text_channel(cid: int, name: str, position: int, category_id: int) -> MagicMock:
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = cid
    channel.name = name
    channel.position = position
    channel.category_id = category_id
    return channel


def make_guild(channels: list[MagicMock]) -> MagicMock:
    guild = MagicMock(spec=discord.Guild)
    guild.id = 1
    guild.fetch_channels = AsyncMock(return_value=channels)
    guild._state = MagicMock()
    guild._state.http.bulk_channel_update = AsyncMock()
    return guild


async def test_category_is_sorted_from_fresh_channels() -> None:
    voice = MagicMock(spec=discord.VoiceChannel)
    voice.category_id = 100
    guild = make_guild(
        [
            text_channel(17, "e017-x", 10, 100),
            text_channel(1, "e001-a", 11, 100),
            text_channel(9, "e009-other", 3, 200),  # 別のカテゴリ
            voice,
        ]
    )

    await sort_category(guild, category_id=100, prefix="e")

    guild._state.http.bulk_channel_update.assert_awaited_once()
    payload = guild._state.http.bulk_channel_update.await_args.args[1]
    assert sorted(payload, key=lambda d: d["id"]) == [
        {"id": 1, "position": 10},
        {"id": 17, "position": 11},
    ]


async def test_failing_to_sort_does_not_raise() -> None:
    guild = make_guild([text_channel(17, "e017-x", 10, 100), text_channel(1, "e001-a", 11, 100)])
    guild._state.http.bulk_channel_update = AsyncMock(
        side_effect=discord.HTTPException(MagicMock(status=500, reason="error"), "error")
    )

    await sort_category(guild, category_id=100, prefix="e")


async def test_unexpected_error_while_sorting_does_not_raise() -> None:
    # discord.pyの内部（_state.http）が変わった場合なども、移動は成功扱いにする
    guild = make_guild([text_channel(17, "e017-x", 10, 100), text_channel(1, "e001-a", 11, 100)])
    guild._state.http.bulk_channel_update = AsyncMock(side_effect=AttributeError("changed"))

    await sort_category(guild, category_id=100, prefix="e")


async def test_moved_channel_is_sorted_by_its_kind_number_in_destination() -> None:
    # 移動してきたc009が、移動前の位置を持ち越してc001より上に入っている
    moved = text_channel(9, "c009-ラーメン", 2, 300)
    moved.edit = AsyncMock()
    guild = make_guild([moved, text_channel(1, "c001-a", 5, 300)])
    moved.guild = guild
    destination = MagicMock(spec=discord.CategoryChannel)
    destination.id = 300

    await move_channel(moved, destination, CLUB)

    moved.edit.assert_awaited_once_with(category=destination, sync_permissions=True)
    payload = guild._state.http.bulk_channel_update.await_args.args[1]
    assert sorted(payload, key=lambda d: d["id"]) == [
        {"id": 1, "position": 2},
        {"id": 9, "position": 3},
    ]
