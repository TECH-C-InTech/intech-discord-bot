"""パネル（ボタンとフォームだけで操作できる画面）"""

from collections.abc import Awaitable, Callable, Sequence
from enum import Enum, StrEnum
from logging import getLogger
import re

import discord

from .kinds import CREATE_ORDER, Kind, kind_of_key
from .linking import NotLinked, collect_kind_categories, link_channel
from .records import Mentionable

logger = getLogger(__name__)

# パネルに名前を並べる参加者の数。超えた分は人数だけ出し、「全員を見る」で本人にだけ見せる
SHOWN_PARTICIPANTS = 20


# パネルは置いたまま何度も書き換えるので、並べた参加者のメンションでは鳴らさない
NO_MENTIONS = discord.AllowedMentions.none()

ARCHIVED_NOTE = "📦 アーカイブ中（このチャンネルでメッセージを送ると戻ります）"


def _participants_text(members: Sequence[Mentionable]) -> str:
    shown = members[:SHOWN_PARTICIPANTS]
    mentions = ", ".join(member.mention for member in shown) or "まだいません"
    rest = len(members) - len(shown)
    if rest > 0:
        mentions += f" ほか{rest}人"
    return f"参加者（{len(members)}人）\n{mentions}"


class ChannelAction(StrEnum):
    """チャンネルのパネルのボタン。値はcustom_idに埋める"""

    JOIN = "join"
    LEAVE = "leave"
    ADD = "add"
    REMOVE = "remove"
    ARCHIVE = "archive"
    RESTORE = "restore"
    SHOW_ALL = "all"


_CHANNEL_BUTTONS: dict[ChannelAction, tuple[str, discord.ButtonStyle]] = {
    ChannelAction.JOIN: ("参加する", discord.ButtonStyle.success),
    ChannelAction.LEAVE: ("抜ける", discord.ButtonStyle.secondary),
    ChannelAction.ADD: ("参加者を追加", discord.ButtonStyle.secondary),
    ChannelAction.REMOVE: ("参加者を外す", discord.ButtonStyle.secondary),
    ChannelAction.ARCHIVE: ("アーカイブ", discord.ButtonStyle.secondary),
    ChannelAction.RESTORE: ("復元", discord.ButtonStyle.primary),
    ChannelAction.SHOW_ALL: ("全員を見る", discord.ButtonStyle.secondary),
}

ChannelPressHandler = Callable[[discord.Interaction, ChannelAction, int], Awaitable[None]]
_channel_press_handler: ChannelPressHandler | None = None


def set_channel_press_handler(handler: ChannelPressHandler) -> None:
    """チャンネルのパネルのボタンが押されたときの処理を登録する（コマンドの登録時に呼ぶ）"""
    global _channel_press_handler
    _channel_press_handler = handler


class ChannelPanelButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"intech:channel:(?P<action>[a-z_]+):(?P<channel_id>[0-9]+)",
):
    """チャンネルのパネルのボタン。custom_idに操作とチャンネルを埋め、botの再起動後も動く"""

    def __init__(self, action: ChannelAction, channel_id: int) -> None:
        label, style = _CHANNEL_BUTTONS[action]
        super().__init__(
            discord.ui.Button(
                label=label, style=style, custom_id=f"intech:channel:{action}:{channel_id}"
            )
        )
        self.action = action
        self.channel_id = channel_id

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Item,
        match: re.Match[str],
        /,
    ) -> "ChannelPanelButton":
        return cls(ChannelAction(match["action"]), int(match["channel_id"]))

    async def callback(self, interaction: discord.Interaction) -> None:
        if _channel_press_handler is None:
            logger.warning(f"No handler for channel panel button {self.custom_id}")
            return
        await _channel_press_handler(interaction, self.action, self.channel_id)


def _custom_ids(components: Sequence[object]) -> list[str]:
    """メッセージの部品をたどって、ボタンなどのcustom_idを集める

    Components V2では、ボタンは枠（Container）や行（ActionRow）、
    文字の横（Section.accessory）に入れ子で届く。
    """
    found: list[str] = []
    for component in components:
        if isinstance(component, (discord.ActionRow, discord.Container)):
            found.extend(_custom_ids(component.children))
        elif isinstance(component, discord.SectionComponent):
            found.extend(_custom_ids([*component.children, component.accessory]))
        else:
            custom_id = getattr(component, "custom_id", None)
            if isinstance(custom_id, str):
                found.append(custom_id)
    return found


def _is_channel_panel(message: discord.Message, bot_id: int) -> bool:
    if message.author.id != bot_id:
        return False
    return any(
        ChannelPanelButton.__discord_ui_compiled_template__.match(custom_id)
        for custom_id in _custom_ids(message.components)
    )


async def find_panel(channel: discord.TextChannel, bot_id: int) -> discord.Message | None:
    """チャンネルのピン留めから、botが置いたチャンネルのパネルを探す"""
    try:
        async for message in channel.pins(limit=None):
            if _is_channel_panel(message, bot_id):
                return message
    except discord.HTTPException as e:
        logger.warning(f"Failed to read pins of {channel.name}: {e}")
    return None


def channel_panel(
    channel: discord.TextChannel, members: Sequence[Mentionable], *, archived: bool
) -> discord.ui.LayoutView:
    """チャンネルのパネル（ピン留めと /intech で共通）

    上に参加者の一覧、下にボタン。ボタンは自分のこと（参加する・抜ける）と、
    みんなのこと（追加・外す・アーカイブ）で行を分ける。
    全員に同じ表示しか出せないので、参加と抜けるは別のボタンにする。
    """

    def button(action: ChannelAction) -> ChannelPanelButton:
        return ChannelPanelButton(action, channel.id)

    participants = _participants_text(members)
    container: discord.ui.Container[discord.ui.LayoutView] = discord.ui.Container(
        accent_colour=discord.Colour.light_grey() if archived else discord.Colour.blurple()
    )
    container.add_item(discord.ui.TextDisplay(f"### #{channel.name}"))
    if archived:
        container.add_item(discord.ui.TextDisplay(ARCHIVED_NOTE))
    if len(members) > SHOWN_PARTICIPANTS:
        container.add_item(
            discord.ui.Section(participants, accessory=button(ChannelAction.SHOW_ALL))
        )
    else:
        container.add_item(discord.ui.TextDisplay(participants))
    container.add_item(discord.ui.Separator())
    container.add_item(
        discord.ui.ActionRow(button(ChannelAction.JOIN), button(ChannelAction.LEAVE))
    )
    container.add_item(
        discord.ui.ActionRow(
            button(ChannelAction.ADD),
            button(ChannelAction.REMOVE),
            button(ChannelAction.RESTORE if archived else ChannelAction.ARCHIVE),
        )
    )
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(container)
    return view


async def refresh_panel(
    channel: discord.TextChannel,
    role: discord.Role,
    *,
    archived: bool,
    joined: Sequence[discord.Member] = (),
    left: Sequence[discord.Member] = (),
) -> bool:
    """ピン留めのパネルを今の参加者と状態に書き換える。パネルがあればTrue

    Args:
        channel: パネルのあるチャンネル
        role: チャンネルのロール
        archived: アーカイブ中か（移動の直後はキャッシュのカテゴリが古いので、呼び出し側が渡す）
        joined: 直前にロールを付けた人
        left: 直前にロールを外した人
    """
    panel = await find_panel(channel, channel.guild.me.id)
    if panel is None:
        return False
    view = channel_panel(
        channel, current_participants(role, joined=joined, left=left), archived=archived
    )
    try:
        await panel.edit(view=view, allowed_mentions=NO_MENTIONS)
    except discord.HTTPException as e:
        logger.warning(f"Failed to refresh panel in {channel.name}: {e}")
    return True


def current_participants(
    role: discord.Role,
    *,
    joined: Sequence[discord.Member] = (),
    left: Sequence[discord.Member] = (),
) -> list[discord.Member]:
    """ロールの参加者に、直前の付け外しを反映する

    ロールの付け外しは、gatewayのイベントが届くまでrole.membersに反映されないため。
    """
    left_ids = {member.id for member in left}
    members = [member for member in role.members if member.id not in left_ids]
    known_ids = {member.id for member in members}
    members.extend(member for member in joined if member.id not in known_ids)
    return members


class Placement(Enum):
    """パネルを置いた結果"""

    PINNED = "pinned"
    # ピン留めできなかったので、投稿を取り下げた
    PIN_FAILED = "pin_failed"
    ALREADY_THERE = "already_there"
    FAILED = "failed"


PIN_FAILED_HELP = (
    "botのロールに「メッセージをピン留め」権限があるか、サーバー管理者に確認してもらってください。"
    "権限を付けたあと、サーバー管理者が`/setup_panel`でパネルを設置し直せます。"
)

# 設置できなかったときに、操作した本人へ伝える (何が起きたか, どうすればよいか)
PLACEMENT_PROBLEMS: dict[Placement, tuple[str, str]] = {
    Placement.PIN_FAILED: (
        "パネルを設置できませんでした（ピン留めできなかったため）。",
        PIN_FAILED_HELP,
    ),
    Placement.FAILED: (
        "パネルを設置できませんでした（メッセージを送れなかったため）。",
        "botがこのチャンネルを見て、メッセージを送れるか、サーバー管理者に確認してもらってください。"
        "権限を直したあと、サーバー管理者が`/setup_panel`でパネルを設置し直せます。",
    ),
}


async def place_panel(
    channel: discord.TextChannel,
    role: discord.Role,
    *,
    archived: bool,
    joined: Sequence[discord.Member] = (),
    new_channel: bool = False,
) -> Placement:
    """チャンネルにパネルを投稿してピン留めする

    すでにパネルがあれば置かない。botにピン留めの権限がなければ投稿しない。
    権限があってもピン留めに失敗したら、投稿を取り下げる
    （パネルはピン留めから探すので、ピン留めされていないパネルは書き換えられず、置き直すと重複する）。

    Args:
        channel: パネルを置くチャンネル
        role: チャンネルのロール
        archived: アーカイブ中か
        joined: 直前にロールを付けた人（作成の直後など）
        new_channel: 作ったばかりのチャンネルか（ピン留めがないので探さない）
    """
    if not new_channel and await find_panel(channel, channel.guild.me.id) is not None:
        return Placement.ALREADY_THERE
    # 投稿してから取り下げると一瞬パネルが見えるので、ピン留めできないと分かっていれば投稿しない
    if not channel.permissions_for(channel.guild.me).pin_messages:
        logger.warning(f"Missing permission to pin panel in {channel.name}")
        return Placement.PIN_FAILED
    view = channel_panel(channel, current_participants(role, joined=joined), archived=archived)
    try:
        message = await channel.send(view=view, allowed_mentions=NO_MENTIONS)
    except discord.HTTPException as e:
        logger.warning(f"Failed to post panel in {channel.name}: {e}")
        return Placement.FAILED
    try:
        await message.pin()
    except discord.HTTPException as e:
        logger.warning(f"Failed to pin panel in {channel.name}: {e}")
        try:
            await message.delete()
        except discord.HTTPException as delete_error:
            logger.warning(f"Failed to withdraw unpinned panel in {channel.name}: {delete_error}")
        return Placement.PIN_FAILED
    return Placement.PINNED


async def refresh_channel_panel(
    guild: discord.Guild,
    names_of: Callable[[Kind], tuple[str, str]],
    channel: discord.TextChannel,
    *,
    archived: bool,
) -> bool:
    """チャンネルのロールを探してパネルを書き換える。パネルがあればTrue

    チャンネルを移動した直後はキャッシュのカテゴリが古いので、アーカイブ中かは呼び出し側が渡す。

    Args:
        guild: サーバー
        names_of: 種類の (通常のカテゴリ名, アーカイブカテゴリ名)
        channel: パネルのあるチャンネル
        archived: アーカイブ中か
    """
    categories, _ = collect_kind_categories(guild.categories, names_of)
    linked = link_channel(channel, guild.roles, categories)
    if isinstance(linked, NotLinked):
        logger.info(f"Skipped refreshing panel of {channel.name}: {linked.reason}")
        return False
    return await refresh_panel(channel, linked.role, archived=archived)


CreatePressHandler = Callable[[discord.Interaction, Kind], Awaitable[None]]
_create_press_handler: CreatePressHandler | None = None


def set_create_press_handler(handler: CreatePressHandler) -> None:
    """作るパネルのボタンが押されたときの処理を登録する（コマンドの登録時に呼ぶ）"""
    global _create_press_handler
    _create_press_handler = handler


class CreatePanelButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"intech:create:(?P<kind>[a-z]+)",
):
    """作るパネルのボタン。custom_idに種類を埋め、botの再起動後も動く"""

    def __init__(self, kind: Kind) -> None:
        super().__init__(
            discord.ui.Button(
                label=f"{kind.label}を作る",
                style=discord.ButtonStyle.primary,
                custom_id=f"intech:create:{kind.key}",
            )
        )
        self.kind = kind

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Item,
        match: re.Match[str],
        /,
    ) -> "CreatePanelButton":
        kind = kind_of_key(match["kind"])
        if kind is None:
            raise ValueError(f"unknown kind in custom_id: {match['kind']}")
        return cls(kind)

    async def callback(self, interaction: discord.Interaction) -> None:
        if _create_press_handler is None:
            logger.warning(f"No handler for create panel button {self.custom_id}")
            return
        await _create_press_handler(interaction, self.kind)


def create_panel() -> discord.ui.LayoutView:
    """作るパネル（案内チャンネルと、チャンネルの外での /intech で共通）"""
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(
        discord.ui.Container(
            discord.ui.TextDisplay("### チャンネルを作る\n誰でも作れます"),
            discord.ui.ActionRow(*(CreatePanelButton(kind) for kind in CREATE_ORDER)),
            accent_colour=discord.Colour.blurple(),
        )
    )
    return view
