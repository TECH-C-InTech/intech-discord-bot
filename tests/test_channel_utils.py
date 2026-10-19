from unittest.mock import MagicMock

import discord

from src.utils.channel_utils import (
    get_next_number,
    resolve_target_text_channel,
)
from src.utils.kinds import CLUB, EVENT


def test_text_channel_targets_itself() -> None:
    channel = MagicMock(spec=discord.TextChannel)

    assert resolve_target_text_channel(channel) == (channel, False)


def test_thread_in_text_channel_targets_parent() -> None:
    parent = MagicMock(spec=discord.TextChannel)
    thread = MagicMock(spec=discord.Thread)
    thread.parent = parent

    assert resolve_target_text_channel(thread) == (parent, True)


def test_thread_in_forum_has_no_target() -> None:
    thread = MagicMock(spec=discord.Thread)
    thread.parent = MagicMock(spec=discord.ForumChannel)

    assert resolve_target_text_channel(thread) == (None, False)


def test_thread_without_parent_has_no_target() -> None:
    thread = MagicMock(spec=discord.Thread)
    thread.parent = None

    assert resolve_target_text_channel(thread) == (None, False)


def test_voice_channel_has_no_target() -> None:
    assert resolve_target_text_channel(MagicMock(spec=discord.VoiceChannel)) == (None, False)


def test_missing_channel_has_no_target() -> None:
    assert resolve_target_text_channel(None) == (None, False)


def make_category(name: str, channel_names: list[str]) -> MagicMock:
    category = MagicMock(spec=discord.CategoryChannel)
    category.name = name
    channels = []
    for channel_name in channel_names:
        channel = MagicMock(spec=discord.TextChannel)
        channel.name = channel_name
        channels.append(channel)
    category.channels = channels
    return category


def make_role(name: str) -> MagicMock:
    role = MagicMock(spec=discord.Role)
    role.name = name
    return role


def test_next_number_avoids_numbers_left_only_on_roles() -> None:
    guild = MagicMock(spec=discord.Guild)
    guild.categories = [make_category("events", ["e003-a"]), make_category("archived", [])]
    # チャンネルだけ消されて、ロールが残っている番号
    guild.roles = [make_role("e010"), make_role("c020-ラーメン")]

    assert get_next_number(guild, EVENT, ("events", "archived")) == 11


def test_next_number_counts_archived_channels_of_the_kind() -> None:
    guild = MagicMock(spec=discord.Guild)
    guild.categories = [
        make_category("clubs", ["c002-a"]),
        make_category("archived-clubs", ["c009-b"]),
    ]
    guild.roles = []

    assert get_next_number(guild, CLUB, ("clubs", "archived-clubs")) == 10
