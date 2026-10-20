"""パネル（ボタンとフォームだけで操作できる画面）のコマンドとボタンの処理"""

from collections.abc import Mapping, Sequence
from logging import getLogger
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from ..utils.channel_actions import archive, join, leave, restore
from ..utils.channel_config import ChannelConfig
from ..utils.channel_utils import get_next_number, resolve_target_text_channel
from ..utils.command_metadata import command_meta
from ..utils.kinds import Kind
from ..utils.linking import (
    Linked,
    NotLinked,
    collect_kind_categories,
    explain_not_linked,
    link_channel,
    locate_channel,
)
from ..utils.message_utils import send_error_message
from ..utils.numbering import NUMBERS_EXHAUSTED, number_of
from ..utils.panel import (
    NO_MENTIONS,
    PIN_FAILED_HELP,
    RESTORE_ON_POST,
    ChannelAction,
    ChannelPanelButton,
    CreatePanelButton,
    Placement,
    channel_panel,
    create_panel,
    current_participants,
    place_panel,
    set_channel_press_handler,
    set_create_press_handler,
)
from ..utils.panel_forms import CreateForm, ParticipantsForm
from ..utils.validation_utils import validate_role_safety

if TYPE_CHECKING:
    from discord.interactions import InteractionChannel

logger = getLogger(__name__)

EMBED_DESCRIPTION_LIMIT = 4096


def choose_panel(
    channel: "InteractionChannel | None",
    roles: Sequence[discord.Role],
    categories: Mapping[Kind, Sequence[discord.CategoryChannel]],
) -> Linked | NotLinked | None:
    """/intech を打った場所に出すパネルを決める

    Returns:
        クラブ・イベント・プロジェクトの番号つきのチャンネル（スレッドなら親）では
        そのチャンネルとロール、
        ロールと紐づかなければその理由、それ以外の場所ではNone（作るパネルを出す）
    """
    target, _ = resolve_target_text_channel(channel)
    if target is None:
        return None
    located = locate_channel(target, categories)
    # 番号のないチャンネル（種類のカテゴリに置いた案内など）では、作るパネルを出す
    if isinstance(located, NotLinked) or number_of(located.kind.prefix, target.name) is None:
        return None
    return link_channel(target, roles, categories)


async def _load(
    ctx: discord.Interaction,
) -> tuple[ChannelConfig, discord.Guild] | None:
    config = await ChannelConfig.load(ctx)
    if not config:
        return None
    if ctx.guild is None:
        await send_error_message(ctx, "サーバーの中でだけ使えます。")
        return None
    return config, ctx.guild


async def intech_impl(ctx: discord.Interaction) -> None:
    """その場所のパネルを本人にだけ出す"""
    loaded = await _load(ctx)
    if loaded is None:
        return
    config, guild = loaded
    categories, missing = collect_kind_categories(guild.categories, config.category_names)
    chosen = choose_panel(ctx.channel, guild.roles, categories)
    if isinstance(chosen, NotLinked):
        await send_error_message(ctx, explain_not_linked(chosen, missing))
        return
    if chosen is None:
        view = create_panel()
    else:
        view = channel_panel(
            chosen.channel, current_participants(chosen.role), archived=chosen.archived
        )
    await ctx.response.send_message(view=view, ephemeral=True, allowed_mentions=NO_MENTIONS)


async def handle_create_press(ctx: discord.Interaction, kind: Kind) -> None:
    """作るパネルのボタン。作るフォームを開く"""
    loaded = await _load(ctx)
    if loaded is None:
        return
    config, guild = loaded
    number = get_next_number(guild, kind, config.category_names(kind))
    if number is None:
        await send_error_message(ctx, NUMBERS_EXHAUSTED)
        return
    await ctx.response.send_modal(
        CreateForm(config, kind, next_number=f"{kind.prefix}{number:03d}")
    )


async def handle_channel_press(
    ctx: discord.Interaction, action: ChannelAction, channel_id: int
) -> None:
    """チャンネルのパネルのボタン。押されるたびに今のチャンネルとロールを取り直す"""
    loaded = await _load(ctx)
    if loaded is None:
        return
    config, guild = loaded
    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        await send_error_message(ctx, "このパネルのチャンネルが見つかりません。")
        return
    categories, missing = collect_kind_categories(guild.categories, config.category_names)
    linked = link_channel(channel, guild.roles, categories)
    if isinstance(linked, NotLinked):
        await send_error_message(ctx, explain_not_linked(linked, missing))
        return
    # 誰でも押せるので、管理者権限を持つロールなどは付け外ししない
    if not await validate_role_safety(ctx, linked.role):
        return

    if action is ChannelAction.JOIN:
        await join(ctx, linked)
    elif action is ChannelAction.LEAVE:
        await leave(ctx, linked)
    elif action in (ChannelAction.ADD, ChannelAction.REMOVE):
        await ctx.response.send_modal(
            ParticipantsForm(config, linked, removing=action is ChannelAction.REMOVE)
        )
    elif action is ChannelAction.ARCHIVE:
        await ask_to_archive(ctx, linked)
    elif action is ChannelAction.CONFIRM_ARCHIVE:
        # 確認のボタンを消してから、もう一度押されないようにする
        await ctx.response.edit_message(view=None)
        await archive(ctx, config, channel)
    elif action is ChannelAction.RESTORE:
        await restore(ctx, config, channel)
    elif action is ChannelAction.SHOW_ALL:
        await show_all_participants(ctx, linked)


async def ask_to_archive(ctx: discord.Interaction, linked: Linked) -> None:
    """アーカイブの前に、押した本人にだけ確認する"""
    if linked.archived:
        await send_error_message(ctx, f"{linked.channel.mention} は既にアーカイブされています。")
        return
    view = discord.ui.View(timeout=None)
    view.add_item(ChannelPanelButton(ChannelAction.CONFIRM_ARCHIVE, linked.channel.id))
    await ctx.response.send_message(
        embed=discord.Embed(
            title=f"#{linked.channel.name} をアーカイブしますか？",
            description=f"アーカイブ中も、{RESTORE_ON_POST}。",
        ),
        view=view,
        ephemeral=True,
    )


def all_participants_text(members: Sequence[discord.Member]) -> str:
    """参加者全員のメンション。Embedの本文の上限に収まらない分は人数で示す"""
    text = ""
    for index, member in enumerate(members):
        addition = (", " if text else "") + member.mention
        rest = f" ほか{len(members) - index}人"
        if len(text) + len(addition) + len(rest) > EMBED_DESCRIPTION_LIMIT:
            return text + rest
        text += addition
    return text or "まだいません"


async def show_all_participants(ctx: discord.Interaction, linked: Linked) -> None:
    """参加者全員を、押した本人にだけ見せる"""
    members = current_participants(linked.role)
    await ctx.response.send_message(
        embed=discord.Embed(
            title=f"#{linked.channel.name} の参加者（{len(members)}人）",
            description=all_participants_text(members),
        ),
        ephemeral=True,
    )


SETUP_HERE_REPLIES = {
    Placement.PINNED: "パネルを設置しました。",
    Placement.PIN_FAILED: (
        f"パネルを設置できませんでした（ピン留めできなかったため）。{PIN_FAILED_HELP}"
    ),
    Placement.ALREADY_THERE: "パネルはすでにあります。",
    Placement.FAILED: (
        "パネルを設置できませんでした。botがこのチャンネルに送信できるか確認してください。"
    ),
}


# 一括の設置はしない。新しいチャンネルには自動で置かれ、既存のチャンネルや
# 置き直しは必要なチャンネルでだけ行う
PANEL_CHOICES = [
    app_commands.Choice(name="チャンネル作成ボタンパネルを設置（当チャンネル）", value="create"),
    app_commands.Choice(name="参加者用ボタンパネルを設置（当チャンネル）", value="here"),
]


async def setup_panel_impl(ctx: discord.Interaction, panel: str) -> None:
    """実行したチャンネルにパネルを設置する（管理者用）"""
    loaded = await _load(ctx)
    if loaded is None:
        return
    config, guild = loaded

    if panel == "create":
        if not isinstance(ctx.channel, discord.abc.Messageable):
            await send_error_message(ctx, "ここには設置できません。")
            return
        await ctx.response.defer(ephemeral=True, thinking=True)
        await ctx.channel.send(view=create_panel())
        await ctx.followup.send("チャンネル作成ボタンパネルを設置しました。", ephemeral=True)
        return

    categories, missing = collect_kind_categories(guild.categories, config.category_names)
    target, _ = resolve_target_text_channel(ctx.channel)
    linked = (
        link_channel(target, guild.roles, categories)
        if target is not None
        else NotLinked("テキストチャンネルかそのスレッドで実行してください。")
    )
    if isinstance(linked, NotLinked):
        await send_error_message(ctx, explain_not_linked(linked, missing))
        return
    await ctx.response.defer(ephemeral=True, thinking=True)
    placement = await place_panel(linked.channel, linked.role, archived=linked.archived)
    await ctx.followup.send(
        f"{linked.channel.mention}: {SETUP_HERE_REPLIES[placement]}", ephemeral=True
    )


def setup(tree: app_commands.CommandTree):
    """パネルのコマンドを登録し、パネルのボタンを再起動後も動くようにする

    デコレーターの順序（重要）:
    1. @command_meta() - メタデータの登録
    2. @tree.command() - コマンドの登録
    3. @app_commands.describe() - パラメータの説明
    """
    set_channel_press_handler(handle_channel_press)
    set_create_press_handler(handle_create_press)
    tree.client.add_dynamic_items(ChannelPanelButton, CreatePanelButton)

    @command_meta(
        category="パネル",
        icon="🎛️",
        short_description="その場所のパネルを自分にだけ出す",
        restrictions=(
            "• クラブ・イベント・プロジェクトのチャンネル（スレッド可）ではそのチャンネルのパネル\n"
            "• それ以外の場所ではチャンネルを作るパネル"
        ),
        examples=["`/intech`"],
    )
    @tree.command(name="intech", description="ボタンで操作できるパネルを、自分にだけ出します")
    async def intech(ctx: discord.Interaction):
        await intech_impl(ctx)

    @command_meta(
        category="パネル",
        icon="🎛️",
        short_description="ボタンで操作できるパネルを設置する（管理者用）",
        restrictions="• サーバーの管理権限が必要",
        examples=[
            "`/setup_panel panel:チャンネル作成ボタンパネルを設置（当チャンネル）` "
            "(案内チャンネルで)",
            "`/setup_panel panel:参加者用ボタンパネルを設置（当チャンネル）` "
            "(クラブ・イベント・プロジェクトのチャンネルで)",
        ],
    )
    @tree.command(name="setup_panel", description="ボタンで操作できるパネルの設置")
    @app_commands.describe(panel="設置するパネル")
    @app_commands.choices(panel=PANEL_CHOICES)
    @app_commands.default_permissions(manage_guild=True)
    async def setup_panel(ctx: discord.Interaction, panel: app_commands.Choice[str]):
        await setup_panel_impl(ctx, panel.value)
