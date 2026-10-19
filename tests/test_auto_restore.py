import asyncio
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.utils.auto_restore import restore_on_post, restore_target
from src.utils.kinds import CLUB, EVENT, PROJECT, Kind

EVENTS_ID, ARCHIVED_ID = 1, 2


def make_category(category_id: int) -> MagicMock:
    category = MagicMock(spec=discord.CategoryChannel)
    category.id = category_id
    return category


CATEGORIES = {EVENT: [make_category(EVENTS_ID), make_category(ARCHIVED_ID)]}


def make_channel(name: str, category_id: int) -> MagicMock:
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = name
    channel.category_id = category_id
    return channel


def make_message(channel: object, *, bot: bool = False) -> MagicMock:
    message = MagicMock(spec=discord.Message)
    message.channel = channel
    message.author = MagicMock(spec=discord.Member)
    message.author.bot = bot
    message.webhook_id = None
    message.type = discord.MessageType.default
    return message


def test_human_post_in_archived_channel_restores_it() -> None:
    channel = make_channel("e003-おでん会", ARCHIVED_ID)

    assert restore_target(make_message(channel), CATEGORIES) == (channel, EVENT)


def test_post_in_own_category_does_not_restore() -> None:
    channel = make_channel("e003-おでん会", EVENTS_ID)

    assert restore_target(make_message(channel), CATEGORIES) is None


def test_post_outside_kind_categories_does_not_restore() -> None:
    channel = make_channel("雑談", category_id=99)

    assert restore_target(make_message(channel), CATEGORIES) is None


def test_post_in_thread_of_archived_channel_restores_parent() -> None:
    parent = make_channel("e003-おでん会", ARCHIVED_ID)
    thread = MagicMock(spec=discord.Thread)
    thread.parent = parent

    assert restore_target(make_message(thread), CATEGORIES) == (parent, EVENT)


def test_direct_message_does_not_restore() -> None:
    dm = MagicMock(spec=discord.DMChannel)

    assert restore_target(make_message(dm), CATEGORIES) is None


def test_bot_post_does_not_restore() -> None:
    channel = make_channel("e003-おでん会", ARCHIVED_ID)

    assert restore_target(make_message(channel, bot=True), CATEGORIES) is None


def test_webhook_post_does_not_restore() -> None:
    message = make_message(make_channel("e003-おでん会", ARCHIVED_ID))
    message.webhook_id = 123

    assert restore_target(message, CATEGORIES) is None


def test_system_message_does_not_restore() -> None:
    message = make_message(make_channel("e003-おでん会", ARCHIVED_ID))
    message.type = discord.MessageType.pins_add

    assert restore_target(message, CATEGORIES) is None


def test_reply_restores() -> None:
    channel = make_channel("e003-おでん会", ARCHIVED_ID)
    message = make_message(channel)
    message.type = discord.MessageType.reply

    assert restore_target(message, CATEGORIES) == (channel, EVENT)


NAMES = {
    CLUB: ("clubs", "archived-clubs"),
    EVENT: ("events", "archived"),
    PROJECT: ("projects", "archived-projects"),
}


def make_guild(channel: MagicMock, *, events_channels: int = 0) -> MagicMock:
    events, archived = make_category(EVENTS_ID), make_category(ARCHIVED_ID)
    events.name, archived.name = "events", "archived"
    events.channels = [MagicMock() for _ in range(events_channels)]
    guild = MagicMock(spec=discord.Guild)
    guild.id = 10
    guild.categories = [events, archived]
    guild.fetch_channel = AsyncMock(return_value=channel)
    guild.fetch_channels = AsyncMock(return_value=[])
    guild._state = MagicMock()
    guild._state.http.bulk_channel_update = AsyncMock()
    channel.guild = guild
    channel.id = 500
    channel.edit = AsyncMock()
    channel.send = AsyncMock()
    return guild


def names_of(kind: Kind) -> tuple[str, str]:
    return NAMES[kind]


async def test_post_moves_archived_channel_back_to_its_category() -> None:
    channel = make_channel("e003-おでん会", ARCHIVED_ID)
    guild = make_guild(channel)
    message = make_message(channel)
    message.guild = guild

    await restore_on_post(message, names_of, locks={})

    channel.edit.assert_awaited_once_with(category=guild.categories[0], sync_permissions=True)


async def test_restore_is_recorded_without_notifying() -> None:
    channel = make_channel("e003-おでん会", ARCHIVED_ID)
    message = make_message(channel)
    message.guild = make_guild(channel)
    message.author.mention = "<@7>"

    await restore_on_post(message, names_of, locks={})

    sent = channel.send.await_args.kwargs
    assert sent["content"] is None
    assert sent["embed"].title == "復元"
    assert sent["embed"].description == (
        "<@7> がメッセージを送ったので、`events` カテゴリーに戻しました"
    )


async def test_channel_already_restored_by_earlier_post_is_left_alone() -> None:
    # キャッシュではまだアーカイブ中だが、最新ではすでに戻っている
    cached = make_channel("e003-おでん会", ARCHIVED_ID)
    guild = make_guild(cached)
    fresh = make_channel("e003-おでん会", EVENTS_ID)
    guild.fetch_channel = AsyncMock(return_value=fresh)
    message = make_message(cached)
    message.guild = guild

    await restore_on_post(message, names_of, locks={})

    cached.edit.assert_not_called()
    cached.send.assert_not_called()


async def test_simultaneous_posts_restore_only_once() -> None:
    channel = make_channel("e003-おでん会", ARCHIVED_ID)
    guild = make_guild(channel)
    current = make_channel("e003-おでん会", ARCHIVED_ID)

    async def fetch_channel(_: int) -> MagicMock:
        await asyncio.sleep(0)
        return current

    async def edit(**kwargs: object) -> None:
        await asyncio.sleep(0)
        current.category_id = EVENTS_ID

    guild.fetch_channel = AsyncMock(side_effect=fetch_channel)
    channel.edit = AsyncMock(side_effect=edit)
    first, second = make_message(channel), make_message(channel)
    first.guild = second.guild = guild
    locks: dict[int, asyncio.Lock] = {}

    await asyncio.gather(
        restore_on_post(first, names_of, locks=locks),
        restore_on_post(second, names_of, locks=locks),
    )

    channel.edit.assert_awaited_once()


async def test_full_destination_keeps_channel_archived_and_replies_why() -> None:
    channel = make_channel("e003-おでん会", ARCHIVED_ID)
    message = make_message(channel)
    message.guild = make_guild(channel, events_channels=50)
    message.reply = AsyncMock()

    await restore_on_post(message, names_of, locks={})

    channel.edit.assert_not_called()
    assert message.reply.await_args.args[0] == (
        "`events` カテゴリーがチャンネル数の上限（50）に達しているため、"
        "このチャンネルを戻せませんでした。サーバー管理者に連絡してください。"
    )


async def test_failed_move_is_not_recorded_and_replies_why() -> None:
    channel = make_channel("e003-おでん会", ARCHIVED_ID)
    message = make_message(channel)
    message.guild = make_guild(channel)
    channel.edit = AsyncMock(
        side_effect=discord.Forbidden(MagicMock(status=403, reason="Forbidden"), "forbidden")
    )

    message.reply = AsyncMock()

    await restore_on_post(message, names_of, locks={})

    channel.send.assert_not_called()
    assert message.reply.await_args.args[0] == (
        "このチャンネルを `events` カテゴリーに戻せませんでした。サーバー管理者に連絡してください。"
    )


async def test_failed_lookup_of_latest_channel_is_not_raised() -> None:
    channel = make_channel("e003-おでん会", ARCHIVED_ID)
    message = make_message(channel)
    message.guild = make_guild(channel)
    message.guild.fetch_channel = AsyncMock(
        side_effect=discord.NotFound(MagicMock(status=404, reason="Not Found"), "gone")
    )

    await restore_on_post(message, names_of, locks={})

    channel.edit.assert_not_called()


def test_post_in_unnumbered_channel_in_archive_does_not_restore() -> None:
    # アーカイブカテゴリに置いた案内用のチャンネルなど
    channel = make_channel("アーカイブについて", ARCHIVED_ID)

    assert restore_target(make_message(channel), CATEGORIES) is None


async def test_bot_post_is_dropped_without_looking_at_categories() -> None:
    message = make_message(make_channel("e003-おでん会", ARCHIVED_ID), bot=True)
    message.guild = MagicMock(spec=discord.Guild)
    type(message.guild).categories = property(lambda _: pytest.fail("looked at categories"))

    await restore_on_post(message, names_of, locks={})
