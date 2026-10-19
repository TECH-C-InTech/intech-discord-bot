from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.panel import (
    ChannelAction,
    ChannelPanelButton,
    channel_panel_embed,
    channel_panel_view,
    create_panel,
    find_panel,
    place_panel,
    refresh_panel,
)


def member(user_id: int) -> MagicMock:
    obj = MagicMock()
    obj.mention = f"<@{user_id}>"
    return obj


def test_channel_panel_shows_channel_name_and_participants() -> None:
    embed = channel_panel_embed("e003-おでん会", [member(1), member(2)])

    assert embed.title == "#e003-おでん会"
    assert embed.description == "参加者（2人）: <@1>, <@2>"


def test_channel_panel_says_no_participants_yet() -> None:
    embed = channel_panel_embed("e003-おでん会", [])

    assert embed.description == "参加者（0人）: まだいません"


def test_channel_panel_shows_first_twenty_and_how_many_more() -> None:
    embed = channel_panel_embed("c005-ラーメン", [member(i) for i in range(1, 24)])

    shown = ", ".join(f"<@{i}>" for i in range(1, 21))
    assert embed.description == f"参加者（23人）: {shown} ほか3人"


def labels(view: object) -> list[str]:
    return [item.item.label for item in view.children]  # type: ignore[attr-defined]


async def test_channel_panel_buttons() -> None:
    view = channel_panel_view(500, archived=False, participants=3)

    assert labels(view) == ["参加する", "抜ける", "参加者を追加", "参加者を外す", "アーカイブ"]


async def test_archived_channel_panel_offers_restore_instead_of_archive() -> None:
    view = channel_panel_view(500, archived=True, participants=3)

    assert labels(view)[-1] == "復元"
    assert "アーカイブ" not in labels(view)


async def test_channel_panel_offers_show_all_when_participants_overflow() -> None:
    assert "全員を見る" not in labels(channel_panel_view(500, archived=False, participants=20))
    assert "全員を見る" in labels(channel_panel_view(500, archived=False, participants=21))


async def test_channel_panel_button_is_restored_from_custom_id() -> None:
    button = channel_panel_view(500, archived=False, participants=0).children[0]
    match = ChannelPanelButton.__discord_ui_compiled_template__.match(button.custom_id)  # type: ignore[attr-defined]
    assert match is not None

    restored = await ChannelPanelButton.from_custom_id(MagicMock(), MagicMock(), match)

    assert (restored.action, restored.channel_id) == (ChannelAction.JOIN, 500)


BOT_ID = 900


class Pins:
    """channel.pins() の戻り値（非同期イテレータ）"""

    def __init__(self, messages: list[MagicMock]) -> None:
        self._messages = iter(messages)

    def __aiter__(self) -> "Pins":
        return self

    async def __anext__(self) -> MagicMock:
        try:
            return next(self._messages)
        except StopIteration:
            raise StopAsyncIteration from None


def pinned(author_id: int, custom_ids: list[str]) -> MagicMock:
    message = MagicMock(spec=discord.Message)
    message.author = MagicMock()
    message.author.id = author_id
    row = MagicMock(spec=discord.ActionRow)
    row.children = [MagicMock(custom_id=custom_id) for custom_id in custom_ids]
    message.components = [row]
    return message


def channel_with_pins(*messages: MagicMock) -> MagicMock:
    channel = MagicMock(spec=discord.TextChannel)
    channel.pins = MagicMock(side_effect=lambda **_: Pins(list(messages)))
    return channel


async def test_find_panel_picks_bots_channel_panel_among_pins() -> None:
    panel = pinned(BOT_ID, ["intech:channel:join:500"])
    channel = channel_with_pins(pinned(1, []), pinned(BOT_ID, ["other"]), panel)

    assert await find_panel(channel, BOT_ID) is panel


async def test_find_panel_returns_none_without_panel() -> None:
    assert await find_panel(channel_with_pins(pinned(1, [])), BOT_ID) is None


async def test_find_panel_returns_none_when_pins_cannot_be_read() -> None:
    channel = MagicMock(spec=discord.TextChannel)
    channel.pins = MagicMock(side_effect=discord.Forbidden(MagicMock(status=403), "Missing Access"))

    assert await find_panel(channel, BOT_ID) is None


def guild_member(user_id: int) -> MagicMock:
    obj = MagicMock(spec=discord.Member)
    obj.id = user_id
    obj.mention = f"<@{user_id}>"
    return obj


def channel_with_panel(panel: MagicMock) -> MagicMock:
    channel = channel_with_pins(panel)
    channel.id = 500
    channel.name = "e003-おでん会"
    channel.guild = MagicMock()
    channel.guild.me.id = BOT_ID
    panel.edit = AsyncMock()
    return channel


def role_with(*members: MagicMock) -> MagicMock:
    role = MagicMock(spec=discord.Role)
    role.members = list(members)
    return role


async def test_refresh_panel_rewrites_participants_and_buttons() -> None:
    panel = pinned(BOT_ID, ["intech:channel:join:500"])
    channel = channel_with_panel(panel)

    await refresh_panel(channel, role_with(guild_member(1)), archived=True)

    sent = panel.edit.await_args.kwargs
    assert sent["embed"].description == "参加者（1人）: <@1>"
    assert labels(sent["view"])[-1] == "復元"


async def test_refresh_panel_reflects_members_changed_just_now() -> None:
    # ロールの付け外しは、gatewayのイベントが届くまでrole.membersに反映されない
    panel = pinned(BOT_ID, ["intech:channel:join:500"])
    channel = channel_with_panel(panel)
    stays, leaves = guild_member(1), guild_member(2)

    await refresh_panel(
        channel,
        role_with(stays, leaves),
        archived=False,
        joined=[guild_member(3)],
        left=[leaves],
    )

    assert panel.edit.await_args.kwargs["embed"].description == "参加者（2人）: <@1>, <@3>"


async def test_refresh_panel_does_not_raise_when_edit_fails() -> None:
    panel = pinned(BOT_ID, ["intech:channel:join:500"])
    channel = channel_with_panel(panel)
    panel.edit.side_effect = discord.HTTPException(MagicMock(status=500), "error")

    await refresh_panel(channel, role_with(), archived=False)


def channel_to_place(*pins: MagicMock) -> tuple[MagicMock, MagicMock]:
    channel = channel_with_pins(*pins)
    channel.id = 500
    channel.name = "e003-おでん会"
    channel.guild = MagicMock()
    channel.guild.me.id = BOT_ID
    posted = MagicMock(spec=discord.Message)
    posted.pin = AsyncMock()
    channel.send = AsyncMock(return_value=posted)
    return channel, posted


async def test_place_panel_posts_and_pins_it() -> None:
    channel, posted = channel_to_place()

    placed = await place_panel(channel, role_with(guild_member(1)), archived=False)

    assert placed is True
    assert channel.send.await_args.kwargs["embed"].title == "#e003-おでん会"
    posted.pin.assert_awaited_once()


async def test_place_panel_keeps_post_when_pin_fails() -> None:
    channel, posted = channel_to_place()
    posted.pin.side_effect = discord.Forbidden(MagicMock(status=403), "Missing Permissions")

    assert await place_panel(channel, role_with(), archived=False) is True


async def test_place_panel_skips_channel_that_already_has_one() -> None:
    channel, _ = channel_to_place(pinned(BOT_ID, ["intech:channel:join:500"]))

    assert await place_panel(channel, role_with(), archived=False) is False
    channel.send.assert_not_called()


async def test_place_panel_returns_false_when_post_fails() -> None:
    channel, _ = channel_to_place()
    channel.send.side_effect = discord.Forbidden(MagicMock(status=403), "Missing Access")

    assert await place_panel(channel, role_with(), archived=False) is False


async def test_create_panel_offers_three_kinds_to_anyone() -> None:
    embed, view = create_panel()

    assert embed.title == "チャンネルを作る"
    assert embed.description == "誰でも作れます"
    assert labels(view) == ["クラブを作る", "イベントを作る", "プロジェクトを作る"]
