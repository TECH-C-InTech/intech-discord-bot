from unittest.mock import MagicMock

import discord

from src.utils.channel_utils import resolve_target_text_channel


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
