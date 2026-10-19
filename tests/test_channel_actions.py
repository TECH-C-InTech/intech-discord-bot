from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.channel_actions import (
    add_participants,
    archive,
    create,
    join,
    leave,
    remove_participants,
    restore,
)
from src.utils.kinds import EVENT
from src.utils.linking import Linked
from tests.ui_helpers import button_labels, texts

BOT_ID = 900


class Pins:
    def __init__(self, messages: list[MagicMock]) -> None:
        self._messages = iter(messages)

    def __aiter__(self) -> "Pins":
        return self

    async def __anext__(self) -> MagicMock:
        try:
            return next(self._messages)
        except StopIteration:
            raise StopAsyncIteration from None


def make_panel() -> MagicMock:
    panel = MagicMock(spec=discord.Message)
    panel.author = MagicMock()
    panel.author.id = BOT_ID
    row = MagicMock(spec=discord.ActionRow)
    row.children = [MagicMock(custom_id="intech:channel:join:500")]
    panel.components = [row]
    panel.edit = AsyncMock()
    return panel


def make_member(user_id: int, *roles: MagicMock) -> MagicMock:
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.mention = f"<@{user_id}>"
    member.roles = list(roles)
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    return member


def make_linked(*members: MagicMock, panel: MagicMock | None = None) -> Linked:
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 500
    channel.name = "e003-おでん会"
    channel.mention = "<#500>"
    channel.guild = MagicMock()
    channel.guild.me.id = BOT_ID
    channel.send = AsyncMock()
    channel.pins = MagicMock(side_effect=lambda **_: Pins([panel] if panel else []))
    role = MagicMock(spec=discord.Role)
    role.mention = "<@&20>"
    role.name = "e003"
    role.members = list(members)
    return Linked(kind=EVENT, channel=channel, role=role)


def make_ctx(user: MagicMock) -> MagicMock:
    ctx = MagicMock(spec=discord.Interaction)
    ctx.user = user
    ctx.response = MagicMock()
    ctx.response.is_done = MagicMock(return_value=False)
    ctx.response.defer = AsyncMock()
    ctx.response.send_message = AsyncMock()
    ctx.followup = MagicMock()
    ctx.followup.send = AsyncMock()
    return ctx


def panel_text(panel: MagicMock) -> str:
    """書き換えたパネルの参加者の一覧"""
    return texts(panel.edit.await_args.kwargs["view"])[-1]


def record_of(linked: Linked) -> discord.Embed:
    return linked.channel.send.await_args.kwargs["embed"]  # type: ignore[attr-defined]


async def test_join_makes_user_a_participant_and_records_it_quietly() -> None:
    panel = make_panel()
    linked = make_linked(panel=panel)
    user = make_member(1)

    await join(make_ctx(user), linked)

    user.add_roles.assert_awaited_once_with(linked.role)
    assert record_of(linked).description == "<@1> が <@&20> に参加しました"
    assert linked.channel.send.await_args.kwargs["content"] is None  # type: ignore[attr-defined]
    assert panel_text(panel) == "参加者（1人）\n<@1>"


def private_text(ctx: MagicMock) -> str:
    """本人への返信の文面（エラーは本文、成功はEmbed）"""
    for call in [*ctx.response.send_message.await_args_list, *ctx.followup.send.await_args_list]:
        if call.args:
            return call.args[0]
        embed = call.kwargs.get("embed")
        if embed is not None:
            return f"{embed.title}\n{embed.description}"
    raise AssertionError("no private reply")


async def test_join_tells_participant_they_already_joined() -> None:
    linked = make_linked()
    user = make_member(1, linked.role)  # type: ignore[arg-type]
    ctx = make_ctx(user)

    await join(ctx, linked)

    user.add_roles.assert_not_called()
    linked.channel.send.assert_not_called()  # type: ignore[attr-defined]
    assert "すでに参加しています" in private_text(ctx)


async def test_leave_removes_user_and_records_it_quietly() -> None:
    panel = make_panel()
    stays = make_member(2)
    linked = make_linked(stays, panel=panel)
    user = make_member(1, linked.role)  # type: ignore[arg-type]
    linked.role.members.append(user)  # type: ignore[attr-defined]

    await leave(make_ctx(user), linked)

    user.remove_roles.assert_awaited_once_with(linked.role)
    assert record_of(linked).description == "<@1> が <@&20> から抜けました"
    assert linked.channel.send.await_args.kwargs["content"] is None  # type: ignore[attr-defined]
    assert panel_text(panel) == "参加者（1人）\n<@2>"


async def test_leave_tells_non_participant_they_have_not_joined() -> None:
    linked = make_linked()
    user = make_member(1)
    ctx = make_ctx(user)

    await leave(ctx, linked)

    user.remove_roles.assert_not_called()
    linked.channel.send.assert_not_called()  # type: ignore[attr-defined]
    assert "参加していません" in private_text(ctx)


async def test_adding_participants_refreshes_panel() -> None:
    panel = make_panel()
    linked = make_linked(make_member(1), panel=panel)

    await add_participants(make_ctx(make_member(1)), linked, [make_member(2)])

    assert panel_text(panel) == "参加者（2人）\n<@1>, <@2>"


async def test_removing_participants_refreshes_panel() -> None:
    panel = make_panel()
    linked = make_linked(panel=panel)
    removed = make_member(2, linked.role)  # type: ignore[arg-type]
    linked.role.members.extend([make_member(1), removed])  # type: ignore[attr-defined]

    await remove_participants(make_ctx(make_member(1)), linked, [removed])

    assert panel_text(panel) == "参加者（1人）\n<@1>"


EVENTS_ID, ARCHIVED_ID = 1, 2


def make_config() -> MagicMock:
    config = MagicMock()
    names = {
        "club": ("clubs", "archived-clubs"),
        "event": ("events", "archived"),
        "project": ("projects", "archived-projects"),
    }
    config.category_names = MagicMock(side_effect=lambda kind: names[kind.key])
    return config


def place_in_guild(linked: Linked, *, archived: bool) -> MagicMock:
    """チャンネルをイベントの通常かアーカイブのカテゴリに置いたサーバーを作る"""
    events = MagicMock(spec=discord.CategoryChannel)
    events.id, events.name, events.channels = EVENTS_ID, "events", []
    archive = MagicMock(spec=discord.CategoryChannel)
    archive.id, archive.name, archive.channels = ARCHIVED_ID, "archived", []
    home = archive if archived else events
    home.text_channels = [linked.channel]
    (events if archived else archive).text_channels = []
    channel = linked.channel
    channel.category_id = home.id  # type: ignore[misc]
    channel.edit = AsyncMock()  # type: ignore[method-assign]
    guild: MagicMock = channel.guild  # type: ignore[assignment]
    guild.id = 10
    guild.categories = [events, archive]
    guild.roles = [linked.role]
    guild.fetch_channels = AsyncMock(return_value=[])
    guild._state.http.bulk_channel_update = AsyncMock()
    linked.role.name = "e003"
    return guild


def ctx_in(guild: MagicMock) -> MagicMock:
    ctx = make_ctx(make_member(1))
    ctx.guild = guild
    return ctx


async def test_archiving_switches_panel_to_restore() -> None:
    panel = make_panel()
    linked = make_linked(panel=panel)
    guild = place_in_guild(linked, archived=False)

    await archive(ctx_in(guild), make_config(), linked.channel)

    assert button_labels(panel.edit.await_args.kwargs["view"])[-1] == "復元"


async def test_restoring_switches_panel_back_to_archive() -> None:
    panel = make_panel()
    linked = make_linked(panel=panel)
    guild = place_in_guild(linked, archived=True)

    await restore(ctx_in(guild), make_config(), linked.channel)

    assert button_labels(panel.edit.await_args.kwargs["view"])[-1] == "アーカイブ"


def guild_to_create_in() -> tuple[MagicMock, MagicMock, MagicMock]:
    """作成先のサーバーと、作られるチャンネル・ロール"""
    events = MagicMock(spec=discord.CategoryChannel)
    events.name, events.channels = "events", []
    guild = MagicMock(spec=discord.Guild)
    guild.id = 11
    guild.categories = [events]
    guild.channels = []
    guild.roles = []
    guild.me = MagicMock(id=BOT_ID)
    guild.fetch_roles = AsyncMock(return_value=[])
    linked = make_linked()
    channel: MagicMock = linked.channel  # type: ignore[assignment]
    role: MagicMock = linked.role  # type: ignore[assignment]
    channel.guild = guild  # type: ignore[misc]
    role.id = 20  # type: ignore[misc]
    posted = MagicMock(spec=discord.Message)
    posted.pin = AsyncMock()
    channel.send = AsyncMock(return_value=posted)  # type: ignore[method-assign]
    guild.create_text_channel = AsyncMock(return_value=channel)
    guild.create_role = AsyncMock(return_value=role)
    guild.get_role = MagicMock(return_value=None)
    return guild, channel, role


async def test_creation_places_panel_and_tells_how_others_join() -> None:
    guild, channel, _ = guild_to_create_in()
    ctx = ctx_in(guild)

    await create(ctx, make_config(), EVENT, "おでん会", [])

    panel = channel.send.await_args_list[-1].kwargs
    assert texts(panel["view"])[0] == "### #e003-おでん会"
    channel.send.return_value.pin.assert_awaited_once()
    assert (
        "参加したい人には、このチャンネルを伝えてください。チャンネルのピン留めから参加できます。"
        in private_text(ctx)
    )
