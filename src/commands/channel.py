"""クラブ・イベント・プロジェクトのチャンネル管理コマンド"""

from collections.abc import Sequence
from logging import getLogger

import discord
from discord import app_commands

from ..utils.channel_actions import (
    add_participants,
    archive,
    create,
    remove_participants,
    restore,
)
from ..utils.channel_config import ChannelConfig
from ..utils.channel_utils import resolve_target_text_channel_or_error
from ..utils.command_metadata import command_meta
from ..utils.kinds import CREATE_ORDER, Kind, kind_of_key
from ..utils.linking import (
    Linked,
    NotLinked,
    collect_kind_categories,
    explain_not_linked,
    link_channel,
    link_role,
)
from ..utils.message_utils import send_error_message
from ..utils.validation_utils import parse_member_mentions, validate_role_safety

logger = getLogger(__name__)

KIND_CHOICES = [app_commands.Choice(name=kind.label, value=kind.key) for kind in CREATE_ORDER]


def _kind_categories(
    guild: discord.Guild, config: ChannelConfig
) -> tuple[dict[Kind, list[discord.CategoryChannel]], list[str]]:
    """種類ごとのカテゴリ（[通常, アーカイブ]の順）と、見つからないカテゴリ名"""
    return collect_kind_categories(guild.categories, config.category_names)


# ==================== コマンド実装関数 ====================


async def create_channel_impl(
    ctx: discord.Interaction,
    kind: Kind,
    channel_name: str,
    members: str | None = None,
):
    """チャンネルとロールを作成する

    Args:
        ctx: Discord Interaction
        kind: 作成する種類
        channel_name: 作成するチャンネル名（番号は自動で付く）
        members: ロールに追加するメンバー（メンション形式）
    """
    config = await ChannelConfig.load(ctx)
    if not config:
        return

    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return

    member_objects: list[discord.Member] = []
    if members:
        parsed_members = await parse_member_mentions(ctx, members, guild)
        if parsed_members is None:
            return
        member_objects = parsed_members

    await create(ctx, config, kind, channel_name, member_objects)


async def archive_channel_impl(
    ctx: discord.Interaction,
    channel: discord.TextChannel | None = None,
):
    """チャンネルをその種類のアーカイブカテゴリへ移す

    Args:
        ctx: Discord Interaction
        channel: アーカイブするチャンネル（省略時は実行チャンネル）
    """
    resolved = await _resolve_channel_to_move(ctx, channel)
    if resolved is None:
        return
    config, target, via_thread = resolved
    await archive(ctx, config, target, via_thread=via_thread)


async def restore_channel_impl(
    ctx: discord.Interaction,
    channel: discord.TextChannel | None = None,
):
    """アーカイブされたチャンネルを、その種類のカテゴリへ戻す

    Args:
        ctx: Discord Interaction
        channel: 復元するチャンネル（省略時は実行チャンネル）
    """
    resolved = await _resolve_channel_to_move(ctx, channel)
    if resolved is None:
        return
    config, target, via_thread = resolved
    await restore(ctx, config, target, via_thread=via_thread)


async def _resolve_channel_to_move(
    ctx: discord.Interaction,
    channel: discord.TextChannel | None,
) -> tuple[ChannelConfig, discord.TextChannel, bool] | None:
    """アーカイブ・復元するチャンネルを決める（省略時は実行チャンネル、スレッドなら親）"""
    config = await ChannelConfig.load(ctx)
    if not config:
        return None
    if ctx.guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return None
    if channel is not None:
        return config, channel, False
    target, via_thread = await resolve_target_text_channel_or_error(ctx)
    if target is None:
        return None
    return config, target, via_thread


async def _resolve_role_target(
    ctx: discord.Interaction,
    role: discord.Role | None,
    members: str,
) -> tuple[Linked, bool, Sequence[discord.Member]] | None:
    """参加者の追加・削除の対象（チャンネルとロール）とメンバーを決める"""
    config = await ChannelConfig.load(ctx)
    if not config:
        return None

    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return None

    categories, missing = _kind_categories(guild, config)
    via_thread = False
    if role is None:
        # 省略時は実行チャンネル（スレッドなら親チャンネル）のロール
        channel, via_thread = await resolve_target_text_channel_or_error(ctx)
        if channel is None:
            return None
        linked = link_channel(channel, guild.roles, categories)
    else:
        linked = link_role(role, guild.roles, categories)
    if isinstance(linked, NotLinked):
        await send_error_message(ctx, explain_not_linked(linked, missing))
        return None

    if not await validate_role_safety(ctx, linked.role):
        return None

    member_objects = await parse_member_mentions(ctx, members, guild)
    if member_objects is None:
        return None
    return linked, via_thread, member_objects


async def add_role_members_impl(
    ctx: discord.Interaction,
    members: str,
    role: discord.Role | None = None,
):
    """ロールに参加者を加える

    Args:
        ctx: Discord Interaction
        members: 加えるメンバー（メンション形式）
        role: 対象のロール（省略時は実行チャンネルのロール）
    """
    resolved = await _resolve_role_target(ctx, role, members)
    if resolved is None:
        return
    linked, via_thread, member_objects = resolved
    await add_participants(ctx, linked, member_objects, via_thread=via_thread)


async def remove_role_members_impl(
    ctx: discord.Interaction,
    members: str,
    role: discord.Role | None = None,
):
    """ロールから参加者を外す

    Args:
        ctx: Discord Interaction
        members: 外すメンバー（メンション形式）
        role: 対象のロール（省略時は実行チャンネルのロール）
    """
    resolved = await _resolve_role_target(ctx, role, members)
    if resolved is None:
        return
    linked, via_thread, member_objects = resolved
    await remove_participants(ctx, linked, member_objects, via_thread=via_thread)


def _kind_of(key: str) -> Kind:
    kind = kind_of_key(key)
    # 選択肢はCREATE_ORDERから作っているので、知らないキーは来ない
    assert kind is not None
    return kind


# ==================== コマンド登録 ====================


def setup(tree: app_commands.CommandTree):
    """チャンネル管理のコマンドを登録する

    デコレーターの順序（重要）:
    1. @command_meta() - メタデータの登録
    2. @tree.command() - コマンドの登録
    3. @app_commands.describe() - パラメータの説明
    """

    @command_meta(
        category="チャンネル管理",
        icon="🏗️",
        short_description="クラブ・イベント・プロジェクトのチャンネルとロールを作成",
        restrictions="• どのチャンネル・スレッドからでも実行可能",
        examples=[
            "`/create_channel category:クラブ channel_name:ラーメン`",
            "`/create_channel category:イベント channel_name:おでん会 members:@user1 @user2`",
        ],
    )
    @tree.command(
        name="create_channel",
        description="クラブ・イベント・プロジェクトのチャンネルを作成します",
    )
    @app_commands.describe(
        category="作成する種類",
        channel_name="作成するチャンネル名（番号は自動で付きます）",
        members="ロールに追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
    )
    @app_commands.choices(category=KIND_CHOICES)
    async def create_channel(
        ctx: discord.Interaction,
        category: app_commands.Choice[str],
        channel_name: str,
        members: str | None = None,
    ):
        await create_channel_impl(ctx, _kind_of(category.value), channel_name, members)

    @command_meta(
        category="チャンネル管理",
        icon="🏗️",
        short_description="チャンネルをアーカイブに移動",
        restrictions=(
            "• channel省略時はクラブ・イベント・プロジェクトのチャンネル内（スレッド可）で実行"
        ),
        examples=[
            "`/archive_channel` (実行チャンネルをアーカイブ)",
            "`/archive_channel channel:#e001-おでん会`",
        ],
    )
    @tree.command(
        name="archive_channel",
        description="チャンネルをアーカイブします",
    )
    @app_commands.describe(
        channel="アーカイブするチャンネル（省略時はコマンド実行チャンネル）",
    )
    async def archive_channel(ctx: discord.Interaction, channel: discord.TextChannel | None = None):
        await archive_channel_impl(ctx, channel)

    @command_meta(
        category="チャンネル管理",
        icon="🏗️",
        short_description="アーカイブからチャンネルを復元",
        restrictions="• channel省略時はアーカイブ中のチャンネル内（スレッド可）で実行",
        examples=[
            "`/restore_channel` (実行チャンネルを復元)",
            "`/restore_channel channel:#e001-おでん会`",
        ],
    )
    @tree.command(
        name="restore_channel",
        description="アーカイブされたチャンネルを元のカテゴリーに戻します",
    )
    @app_commands.describe(
        channel="復元するチャンネル（省略時はコマンド実行チャンネル）",
    )
    async def restore_channel(ctx: discord.Interaction, channel: discord.TextChannel | None = None):
        await restore_channel_impl(ctx, channel)

    @command_meta(
        category="ロール管理",
        icon="👥",
        short_description="チャンネルのロールに参加者を追加",
        restrictions="• クラブ・イベント・プロジェクトのロールだけ（アーカイブ中も可）",
        examples=[
            "`/add_role_members members:@user1 @user2`",
            "`/add_role_members members:@user1 role:@e001`",
        ],
    )
    @tree.command(
        name="add_role_members",
        description="チャンネルに紐づくロールに参加者を追加します",
    )
    @app_commands.describe(
        members="追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
        role="参加者を追加するロール（例: @e001。省略時は実行チャンネルのロール）",
    )
    async def add_role_members(
        ctx: discord.Interaction, members: str, role: discord.Role | None = None
    ):
        await add_role_members_impl(ctx, members, role)

    @command_meta(
        category="ロール管理",
        icon="👥",
        short_description="チャンネルのロールから参加者を外す",
        restrictions="• クラブ・イベント・プロジェクトのロールだけ（アーカイブ中も可）",
        examples=[
            "`/remove_role_members members:@user1`",
            "`/remove_role_members members:@user1 role:@e001`",
        ],
    )
    @tree.command(
        name="remove_role_members",
        description="チャンネルに紐づくロールから参加者を外します",
    )
    @app_commands.describe(
        members="外すメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
        role="参加者を外すロール（例: @e001。省略時は実行チャンネルのロール）",
    )
    async def remove_role_members(
        ctx: discord.Interaction, members: str, role: discord.Role | None = None
    ):
        await remove_role_members_impl(ctx, members, role)
