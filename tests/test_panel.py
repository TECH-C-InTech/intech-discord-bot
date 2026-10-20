from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.panel import (
    ChannelAction,
    ChannelPanelButton,
    Placement,
    channel_panel,
    create_panel,
    find_panel,
    place_panel,
    refresh_panel,
)
from tests.ui_helpers import button_labels, custom_ids, texts


def member(user_id: int) -> MagicMock:
    obj = MagicMock()
    obj.mention = f"<@{user_id}>"
    return obj


def make_channel(name: str = "e003-おでん会", channel_id: int = 500) -> MagicMock:
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = name
    channel.id = channel_id
    return channel


async def test_channel_panel_shows_channel_name_and_participants() -> None:
    view = channel_panel(make_channel(), [member(1), member(2)], archived=False)

    assert texts(view) == ["### #e003-おでん会", "参加者（2人）\n<@1>, <@2>"]


async def test_channel_panel_says_no_participants_yet() -> None:
    view = channel_panel(make_channel(), [], archived=False)

    assert texts(view)[-1] == "参加者（0人）\nまだいません"


async def test_channel_panel_shows_first_twenty_and_how_many_more() -> None:
    view = channel_panel(
        make_channel("c005-ラーメン"), [member(i) for i in range(1, 24)], archived=False
    )

    shown = ", ".join(f"<@{i}>" for i in range(1, 21))
    assert texts(view)[-1] == f"参加者（23人）\n{shown} ほか3人"


async def test_channel_panel_separates_own_and_shared_actions() -> None:
    view = channel_panel(make_channel(), [member(1)], archived=False)

    rows = [
        [item.item.label for item in row.children]  # type: ignore[attr-defined]
        for row in view.walk_children()
        if isinstance(row, discord.ui.ActionRow)
    ]
    assert rows == [["参加する", "抜ける"], ["参加者を追加", "参加者を外す", "アーカイブ"]]


async def test_archived_channel_panel_says_so_and_offers_restore() -> None:
    view = channel_panel(make_channel(), [], archived=True)

    assert "📦 アーカイブ中（このチャンネルでメッセージを送ると戻ります）" in texts(view)
    assert button_labels(view)[-1] == "復元"
    assert "アーカイブ" not in button_labels(view)


async def test_channel_panel_offers_show_all_beside_list_when_participants_overflow() -> None:
    few = channel_panel(make_channel(), [member(i) for i in range(20)], archived=False)
    many = channel_panel(make_channel(), [member(i) for i in range(21)], archived=False)

    assert "全員を見る" not in button_labels(few)
    sections = [item for item in many.walk_children() if isinstance(item, discord.ui.Section)]
    assert [section.accessory.item.label for section in sections] == ["全員を見る"]  # type: ignore[attr-defined]


async def test_channel_panel_button_is_restored_from_custom_id() -> None:
    custom_id = custom_ids(channel_panel(make_channel(), [], archived=False))[0]
    match = ChannelPanelButton.__discord_ui_compiled_template__.match(custom_id)
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


async def test_find_panel_finds_buttons_nested_in_layout() -> None:
    # Components V2では、ボタンは枠（Container）や行の中に入れ子で届く
    button = MagicMock(spec=discord.Button)
    button.custom_id = "intech:channel:all:500"
    section = MagicMock(spec=discord.SectionComponent)
    section.children = []
    section.accessory = button
    container = MagicMock(spec=discord.Container)
    container.children = [section]
    panel = pinned(BOT_ID, [])
    panel.components = [container]

    assert await find_panel(channel_with_pins(panel), BOT_ID) is panel


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
    assert "参加者（1人）\n<@1>" in texts(sent["view"])
    assert button_labels(sent["view"])[-1] == "復元"


async def test_panel_never_notifies_listed_participants() -> None:
    # パネルの一覧はメンションで並べるが、書き換えるたびに鳴らさない
    panel = pinned(BOT_ID, ["intech:channel:join:500"])
    channel = channel_with_panel(panel)

    await refresh_panel(channel, role_with(guild_member(1)), archived=False)

    mentions = panel.edit.await_args.kwargs["allowed_mentions"]
    assert (mentions.users, mentions.roles, mentions.everyone) == (False, False, False)


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

    assert "参加者（2人）\n<@1>, <@3>" in texts(panel.edit.await_args.kwargs["view"])


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

    assert placed is Placement.PINNED
    sent = channel.send.await_args.kwargs
    assert texts(sent["view"])[0] == "### #e003-おでん会"
    assert sent["allowed_mentions"].users is False
    posted.pin.assert_awaited_once()


async def test_place_panel_does_not_post_without_pin_permission() -> None:
    # 投稿してから取り下げると、一瞬パネルが見えてしまうため
    channel, _ = channel_to_place()
    channel.permissions_for = MagicMock(return_value=discord.Permissions(send_messages=True))

    assert await place_panel(channel, role_with(), archived=False) is Placement.PIN_FAILED
    channel.send.assert_not_called()


async def test_place_panel_withdraws_post_when_pin_fails() -> None:
    # ピン留めされていないパネルは見つけられず、書き換わらないうえに置き直すと重複するため
    channel, posted = channel_to_place()
    posted.pin.side_effect = discord.Forbidden(MagicMock(status=403), "Missing Permissions")
    posted.delete = AsyncMock()

    assert await place_panel(channel, role_with(), archived=False) is Placement.PIN_FAILED
    posted.delete.assert_awaited_once()


async def test_new_channel_gets_panel_without_looking_at_pins() -> None:
    channel, _ = channel_to_place()

    await place_panel(channel, role_with(), archived=False, new_channel=True)

    channel.pins.assert_not_called()


async def test_place_panel_skips_channel_that_already_has_one() -> None:
    channel, _ = channel_to_place(pinned(BOT_ID, ["intech:channel:join:500"]))

    assert await place_panel(channel, role_with(), archived=False) is Placement.ALREADY_THERE
    channel.send.assert_not_called()


async def test_place_panel_tells_when_post_fails() -> None:
    channel, _ = channel_to_place()
    channel.send.side_effect = discord.Forbidden(MagicMock(status=403), "Missing Access")

    assert await place_panel(channel, role_with(), archived=False) is Placement.FAILED


async def test_create_panel_offers_three_kinds_to_anyone() -> None:
    view = create_panel()

    assert texts(view) == ["### チャンネルを作る\n誰でも作れます"]
    assert button_labels(view) == ["イベントを作る", "プロジェクトを作る", "クラブを作る"]


async def test_show_all_button_is_found_again_from_posted_message() -> None:
    # botの再起動後は、届いたメッセージの部品からボタンを作り直して処理する
    from discord.components import _component_factory

    view = channel_panel(make_channel(), [member(i) for i in range(21)], archived=False)
    message = MagicMock(spec=discord.Message)
    message.components = [_component_factory(data) for data in view.to_components()]

    rebuilt = discord.ui.LayoutView.from_message(message)

    assert "intech:channel:all:500" in [
        getattr(item, "custom_id", None) for item in rebuilt.walk_children()
    ]
