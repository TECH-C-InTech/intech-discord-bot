from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.commands.panel import (
    all_participants_text,
    choose_panel,
    handle_channel_press,
    intech_impl,
    setup_panel_impl,
)
from src.utils.kinds import EVENT
from src.utils.linking import Linked, NotLinked
from src.utils.panel import ChannelAction


def make_channel(name: str, category_id: int) -> MagicMock:
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = name
    channel.category_id = category_id
    channel.mention = f"#{name}"
    return channel


def make_categories(*channels: MagicMock) -> dict:
    events = MagicMock(spec=discord.CategoryChannel)
    events.id = 1
    events.text_channels = list(channels)
    archived = MagicMock(spec=discord.CategoryChannel)
    archived.id = 2
    archived.text_channels = []
    return {EVENT: [events, archived]}


def make_role(name: str) -> MagicMock:
    role = MagicMock(spec=discord.Role)
    role.name = name
    role.permissions = discord.Permissions.none()
    role.managed = False
    role.is_default = MagicMock(return_value=False)
    return role


def test_intech_in_kind_channel_shows_its_panel() -> None:
    channel = make_channel("e003-おでん会", 1)
    role = make_role("e003")

    chosen = choose_panel(channel, [role], make_categories(channel))

    assert chosen == Linked(kind=EVENT, channel=channel, role=role)


def test_intech_in_thread_of_kind_channel_shows_parents_panel() -> None:
    channel = make_channel("e003-おでん会", 1)
    thread = MagicMock(spec=discord.Thread)
    thread.parent = channel
    role = make_role("e003")

    chosen = choose_panel(thread, [role], make_categories(channel))

    assert isinstance(chosen, Linked) and chosen.channel is channel


def test_intech_outside_kind_channels_shows_create_panel() -> None:
    assert choose_panel(make_channel("雑談", 99), [], make_categories()) is None


def test_intech_in_unnumbered_channel_of_kind_category_shows_create_panel() -> None:
    # 種類のカテゴリに置いた案内用のチャンネルなど
    guide = make_channel("はじめに", 1)

    assert choose_panel(guide, [], make_categories(guide)) is None


def test_intech_in_kind_channel_without_role_explains_why() -> None:
    channel = make_channel("e003-おでん会", 1)

    assert isinstance(choose_panel(channel, [], make_categories(channel)), NotLinked)


def mention(user_id: int) -> MagicMock:
    member = MagicMock(spec=discord.Member)
    member.mention = f"<@{user_id}>"
    return member


def test_all_participants_are_listed() -> None:
    assert all_participants_text([mention(1), mention(2)]) == "<@1>, <@2>"


def test_all_participants_beyond_embed_limit_are_counted() -> None:
    members = [mention(10**17 + i) for i in range(300)]

    text = all_participants_text(members)

    assert len(text) <= 4096
    assert text.endswith("人")
    shown = text.count("<@")
    assert text.endswith(f" ほか{300 - shown}人")


def press_setup(monkeypatch: pytest.MonkeyPatch, *, archived: bool) -> tuple[MagicMock, MagicMock]:
    """パネルのボタンが押されたときのInteractionと、押されたチャンネル"""
    channel = make_channel("e003-おでん会", 2 if archived else 1)
    channel.id = 500
    categories = make_categories() if archived else make_categories(channel)
    if archived:
        categories[EVENT][1].text_channels = [channel]
    names = {"club": ("clubs", "ac"), "event": ("events", "archived"), "project": ("p", "ap")}
    config = MagicMock()
    config.category_names = MagicMock(side_effect=lambda kind: names[kind.key])
    monkeypatch.setattr("src.commands.panel.ChannelConfig.load", AsyncMock(return_value=config))
    events, archive = categories[EVENT]
    events.name, archive.name = "events", "archived"
    guild = MagicMock(spec=discord.Guild)
    guild.categories = [events, archive]
    guild.roles = [make_role("e003")]
    guild.get_channel = MagicMock(return_value=channel)
    ctx = MagicMock(spec=discord.Interaction)
    ctx.guild = guild
    ctx.response = MagicMock()
    ctx.response.is_done = MagicMock(return_value=False)
    ctx.response.send_message = AsyncMock()
    ctx.response.send_modal = AsyncMock()
    ctx.response.edit_message = AsyncMock()
    return ctx, channel


async def test_archive_button_asks_presser_to_confirm(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx, _ = press_setup(monkeypatch, archived=False)

    await handle_channel_press(ctx, ChannelAction.ARCHIVE, 500)

    sent = ctx.response.send_message.await_args.kwargs
    assert sent["ephemeral"] is True
    assert sent["embed"].title == "#e003-おでん会 をアーカイブしますか？"
    assert sent["view"].children[0].item.label == "アーカイブする"


async def test_confirming_archive_removes_button_then_archives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, channel = press_setup(monkeypatch, archived=False)
    archive = AsyncMock()
    monkeypatch.setattr("src.commands.panel.archive", archive)

    await handle_channel_press(ctx, ChannelAction.CONFIRM_ARCHIVE, 500)

    ctx.response.edit_message.assert_awaited_once_with(view=None)
    assert archive.await_args is not None
    assert archive.await_args.args[2] is channel


async def test_archive_button_on_archived_channel_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, _ = press_setup(monkeypatch, archived=True)

    await handle_channel_press(ctx, ChannelAction.ARCHIVE, 500)

    assert "既にアーカイブされています" in ctx.response.send_message.await_args.args[0]


async def test_add_button_opens_add_form(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx, _ = press_setup(monkeypatch, archived=False)

    await handle_channel_press(ctx, ChannelAction.ADD, 500)

    assert ctx.response.send_modal.await_args.args[0].title == "参加者を追加"


async def test_button_for_vanished_channel_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx, _ = press_setup(monkeypatch, archived=False)
    ctx.guild.get_channel = MagicMock(return_value=None)

    await handle_channel_press(ctx, ChannelAction.JOIN, 500)

    assert "見つかりません" in ctx.response.send_message.await_args.args[0]


async def test_join_button_refuses_role_with_administrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, _ = press_setup(monkeypatch, archived=False)
    role = ctx.guild.roles[0]
    role.permissions = discord.Permissions(administrator=True)
    join = AsyncMock()
    monkeypatch.setattr("src.commands.panel.join", join)

    await handle_channel_press(ctx, ChannelAction.JOIN, 500)

    join.assert_not_called()


def setup_ctx(monkeypatch: pytest.MonkeyPatch, *categories: MagicMock) -> MagicMock:
    # イベントとプロジェクトがアーカイブカテゴリを共有している
    names = {
        "club": ("clubs", "archived-clubs"),
        "event": ("events", "archived"),
        "project": ("projects", "archived"),
    }
    config = MagicMock()
    config.category_names = MagicMock(side_effect=lambda kind: names[kind.key])
    monkeypatch.setattr("src.commands.panel.ChannelConfig.load", AsyncMock(return_value=config))
    ctx = MagicMock(spec=discord.Interaction)
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.categories = list(categories)
    ctx.guild.roles = [make_role("e001"), make_role("p001")]
    ctx.response = MagicMock()
    ctx.response.is_done = MagicMock(return_value=False)
    ctx.response.defer = AsyncMock()
    ctx.response.send_message = AsyncMock()
    ctx.followup = MagicMock()
    ctx.followup.send = AsyncMock()
    return ctx


def named(category_id: int, name: str, *channels: MagicMock) -> MagicMock:
    category = MagicMock(spec=discord.CategoryChannel)
    category.id, category.name, category.text_channels = category_id, name, list(channels)
    return category


async def test_setup_all_places_panel_once_per_channel_in_shared_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event, project = make_channel("e001-a", 2), make_channel("p001-b", 2)
    ctx = setup_ctx(
        monkeypatch, named(1, "events"), named(3, "projects"), named(2, "archived", event, project)
    )
    place = AsyncMock(return_value=True)
    monkeypatch.setattr("src.commands.panel.place_panel", place)

    await setup_panel_impl(ctx, "all")

    assert sorted(call.args[0].name for call in place.await_args_list) == ["e001-a", "p001-b"]
    assert "2個のチャンネルにパネルを置きました" in ctx.followup.send.await_args.args[0]


async def test_setup_here_outside_kind_channel_explains_why(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = setup_ctx(monkeypatch, named(1, "events"), named(3, "projects"), named(2, "archived"))
    ctx.channel = make_channel("雑談", 99)

    await setup_panel_impl(ctx, "here")

    assert "ではありません" in ctx.response.send_message.await_args.args[0]


async def test_intech_channel_panel_does_not_notify_listed_participants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, channel = press_setup(monkeypatch, archived=False)
    ctx.channel = channel
    ctx.guild.roles[0].members = []

    await intech_impl(ctx)

    mentions = ctx.response.send_message.await_args.kwargs["allowed_mentions"]
    assert (mentions.users, mentions.roles, mentions.everyone) == (False, False, False)
