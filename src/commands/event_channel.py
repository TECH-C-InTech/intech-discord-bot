"""イベントチャンネル管理コマンド"""

from logging import getLogger
import re

import discord
from discord import app_commands

from ..utils.capacity import check_move_capacity
from ..utils.channel_config import ChannelConfig
from ..utils.channel_utils import (
    get_next_event_index,
    resolve_target_text_channel_or_error,
    thread_target_note,
    validate_category_exists,
)
from ..utils.command_metadata import command_meta
from ..utils.creation import Created, create_channel_with_role
from ..utils.message_utils import (
    create_success_embed,
    handle_command_error,
    report_creation_problem,
    send_error_message,
    send_private_reply,
)
from ..utils.records import (
    build_archive_notice_embed,
    build_archived_log_embed,
    build_creation_embed,
    build_members_added_embed,
    build_restored_embed,
    post_channel_record,
    post_log,
)
from ..utils.role_utils import describe_grant, grant_role, with_creator
from ..utils.validation_utils import (
    parse_member_mentions,
    parse_role_mention,
    validate_channel_in_category,
    validate_role_safety,
)

logger = getLogger(__name__)

PERMISSION_HELP = (
    "サーバー管理者に、`{category}`, `{archive}`のカテゴリに「権限の管理」"
    "権限がInTech Botのみに付与されているか確認してください。"
)


# ==================== コマンド実装関数 ====================


async def create_event_channel_impl(
    ctx: discord.Interaction,
    channel_name: str,
    members: str | None = None,
):
    """イベントチャンネルを作成する

    Args:
        ctx: Discord Interaction
        channel_name: 作成するイベントチャンネル名
        members: ロールに追加するメンバー（メンション形式）
    """
    # 環境変数を一括取得
    config = await ChannelConfig.load(ctx)
    if not config:
        return

    # カテゴリーの存在確認
    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return

    category_channel = await validate_category_exists(ctx, guild, config.event_category_name)
    if not category_channel:
        return

    # メンバーが指定されている場合、メンションから抽出
    member_objects: list[discord.Member] = []
    if members:
        parsed_members = await parse_member_mentions(ctx, members, guild)
        if parsed_members is None:
            return
        member_objects = parsed_members

    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    def decide_name(guild: discord.Guild, category: discord.CategoryChannel) -> str:
        # 採番はLockの中で行い、並行した作成で番号が重ならないようにする
        next_index = get_next_event_index(
            guild,
            config.event_category_name,
            config.archive_event_category_name,
        )
        # チャンネル名を e{index:03d}-{name} の形式で構築（3桁0埋め）
        return f"e{next_index:03d}-{channel_name}"

    try:
        outcome = await create_channel_with_role(
            guild,
            category_channel,
            decide_name=decide_name,
            # ロール名はチャンネル名の番号部分（e001）
            role_name_for=lambda channel: channel.name.split("-", 1)[0],
        )
    except Exception as e:
        await handle_command_error(ctx, e, "チャンネルの作成")
        return

    if not isinstance(outcome, Created):
        await report_creation_problem(ctx, outcome, "チャンネルの作成")
        return

    channel, role = outcome.channel, outcome.role
    # 立てた人は、その時点で参加者になる
    participants = (
        with_creator(member_objects, ctx.user)
        if isinstance(ctx.user, discord.Member)
        else member_objects
    )
    grant = await grant_role(participants, role)

    description = f"{channel.mention} と {role.mention} を作成しました"
    grant_description = describe_grant(grant)
    if grant_description:
        description += f"\n{grant_description}"
    await send_private_reply(
        ctx,
        create_success_embed(
            title="イベントチャンネル作成完了",
            description=description,
            チャンネル名=channel.name,
            ロール付与人数=len(grant.granted),
        ),
    )
    logger.info(
        f"Created channel: {channel.name} and role {role.name} "
        f"with {len(grant.granted)} members by {ctx.user}"
    )

    def record() -> discord.Embed:
        return build_creation_embed(
            kind="イベント",
            actor=ctx.user,
            channel=channel,
            role=role,
            members=grant.granted,
            failed_members=grant.failed,
            join_command="/add_event_role_member",
        )

    await post_channel_record(
        channel, record(), mention_users=grant.granted, mention_label="参加者"
    )
    await post_log(guild, config.log_channel_name, record())


async def archive_event_channel_impl(
    ctx: discord.Interaction,
    channel_name: discord.TextChannel | None = None,
):
    """イベントチャンネルをアーカイブする

    Args:
        ctx: Discord Interaction
        channel_name: アーカイブするチャンネル名（省略時は実行チャンネル）
    """
    # 環境変数を一括取得
    config = await ChannelConfig.load(ctx)
    if not config:
        return

    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return

    # アーカイブ先カテゴリーの存在確認
    archive_category_channel = await validate_category_exists(
        ctx, guild, config.archive_event_category_name
    )
    if not archive_category_channel:
        return

    # 移動するチャンネルを特定（スレッドから実行された場合は親チャンネル）
    channel: discord.TextChannel | None = channel_name
    via_thread = False
    if channel is None:
        channel, via_thread = await resolve_target_text_channel_or_error(ctx)
        if channel is None:
            return

    # チャンネルがイベントカテゴリーに属しているか確認
    if not await validate_channel_in_category(ctx, channel, config.event_category_name):
        return

    capacity_reason = check_move_capacity(
        destination_category_channels=len(archive_category_channel.channels)
    )
    if capacity_reason is not None:
        await send_error_message(ctx, capacity_reason)
        return

    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    # アーカイブ先ではbotが送信できない可能性があるため、移動の前に記録を残す
    notice = await post_channel_record(
        channel,
        build_archive_notice_embed(actor=ctx.user, restore_command="/restore_event_channel"),
    )

    try:
        await channel.edit(category=archive_category_channel, sync_permissions=True)
    except Exception as e:
        if notice is not None:
            try:
                await notice.delete()
            except discord.HTTPException as delete_error:
                logger.warning(f"Failed to delete archive notice: {delete_error}")
        await handle_command_error(
            ctx,
            e,
            "チャンネルのアーカイブ",
            custom_help_texts={
                discord.Forbidden: PERMISSION_HELP.format(
                    category=config.event_category_name,
                    archive=config.archive_event_category_name,
                )
            },
        )
        return

    await send_private_reply(
        ctx,
        create_success_embed(
            title="イベントチャンネルアーカイブ完了",
            description=(
                f"{channel.mention} をアーカイブしました{thread_target_note(channel, via_thread)}"
            ),
            チャンネル名=channel.name,
        ),
    )
    logger.info(f"Archived channel: {channel.name} by {ctx.user}")

    await post_log(
        guild,
        config.log_channel_name,
        build_archived_log_embed(
            actor=ctx.user, channel=channel, restore_command="/restore_event_channel"
        ),
    )


async def restore_event_channel_impl(
    ctx: discord.Interaction,
    channel_name: discord.TextChannel | None = None,
):
    """アーカイブされたイベントチャンネルを復元する

    Args:
        ctx: Discord Interaction
        channel_name: 復元するチャンネル名（省略時は実行チャンネル）
    """
    # 環境変数を一括取得
    config = await ChannelConfig.load(ctx)
    if not config:
        return

    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return

    # イベントカテゴリーの存在確認
    event_category_channel = await validate_category_exists(ctx, guild, config.event_category_name)
    if not event_category_channel:
        return

    # 移動するチャンネルを特定（スレッドから実行された場合は親チャンネル）
    channel: discord.TextChannel | None = channel_name
    via_thread = False
    if channel is None:
        channel, via_thread = await resolve_target_text_channel_or_error(ctx)
        if channel is None:
            return

    if not await validate_channel_in_category(ctx, channel, config.archive_event_category_name):
        return

    capacity_reason = check_move_capacity(
        destination_category_channels=len(event_category_channel.channels)
    )
    if capacity_reason is not None:
        await send_error_message(ctx, capacity_reason)
        return

    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    try:
        await channel.edit(category=event_category_channel, sync_permissions=True)
    except Exception as e:
        await handle_command_error(
            ctx,
            e,
            "チャンネルの復元",
            custom_help_texts={
                discord.Forbidden: PERMISSION_HELP.format(
                    category=config.event_category_name,
                    archive=config.archive_event_category_name,
                )
            },
        )
        return

    await send_private_reply(
        ctx,
        create_success_embed(
            title="イベントチャンネル復元完了",
            description=(
                f"{channel.mention} を復元しました{thread_target_note(channel, via_thread)}"
            ),
            チャンネル名=channel.name,
        ),
    )
    logger.info(f"Restored channel: {channel.name} by {ctx.user}")

    await post_channel_record(channel, build_restored_embed(actor=ctx.user, channel=channel))
    await post_log(
        guild,
        config.log_channel_name,
        build_restored_embed(actor=ctx.user, channel=channel),
    )


async def add_event_role_member_impl(
    ctx: discord.Interaction,
    members: str,
    role_name: str | None = None,
):
    """イベントロールにメンバーを追加する

    実行可能なロールはEVENT_CATEGORY_NAMEカテゴリのチャンネルに対応するものだけ

    Args:
        ctx: Discord Interaction
        members: 追加するメンバー（メンション形式）
        role_name: 対象のロール名（省略時は実行チャンネル名）
    """
    # 環境変数を一括取得
    config = await ChannelConfig.load(ctx)
    if not config:
        return

    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return

    # カテゴリーの存在確認
    event_category = await validate_category_exists(ctx, guild, config.event_category_name)
    if not event_category:
        return

    via_thread = False
    # role_nameが省略された場合は実行チャンネル（スレッドなら親チャンネル）のロールを使用
    if role_name is None:
        target_channel, via_thread = await resolve_target_text_channel_or_error(ctx)
        if target_channel is None:
            return
        # 対象チャンネルがEVENT_CATEGORY_NAMEカテゴリーに属しているか確認
        if not await validate_channel_in_category(ctx, target_channel, config.event_category_name):
            return
        # チャンネル名からindexを抽出して、e{index}形式のロールを検索
        # チャンネル名: e001-xxx -> index: 001
        match = re.match(r"^e(\d{3})-", target_channel.name)
        if not match:
            await send_error_message(
                ctx, "このチャンネルはイベントチャンネルの形式（e001-xxx）ではありません。"
            )
            return
        channel_index = int(match.group(1))
        role_name_to_find = f"e{channel_index:03d}"
        role = discord.utils.get(guild.roles, name=role_name_to_find)
        if not role:
            await send_error_message(ctx, f"ロール `{role_name_to_find}` が見つかりません。")
            return
    else:
        # role_nameが指定された場合、パース関数でロールを取得
        role = await parse_role_mention(ctx, role_name, guild)
        if not role:
            return

    # ロールの安全性チェック
    if not await validate_role_safety(ctx, role):
        return

    # ロール名から数字部分を抽出（e001 -> 1）
    role_match = re.match(r"^e(\d{3})$", role.name)
    if not role_match:
        await send_error_message(
            ctx,
            f"ロール {role.mention} はイベントロールの形式（e001形式）ではありません。",
        )
        return

    role_index = int(role_match.group(1))

    # 同名のチャンネルがEVENT_CATEGORY_NAMEカテゴリーに存在するか確認
    # e{index:03d}-で始まるチャンネルを検索（3桁0埋め）
    event_channel = None
    for ch in event_category.text_channels:
        if ch.name.startswith(f"e{role_index:03d}-"):
            event_channel = ch
            break

    if not event_channel:
        await send_error_message(
            ctx,
            f"ロール {role.mention} に対応するイベントチャンネルが見つかりません。\n"
            f"このコマンドは{config.event_category_name}カテゴリー内のチャンネルに対応するロールのみ操作可能です。",
        )
        return

    # メンバーをメンションから抽出
    member_objects = await parse_member_mentions(ctx, members, guild)
    if member_objects is None:
        return

    # 応答を保留
    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    grant = await grant_role(member_objects, role)

    note = thread_target_note(event_channel, via_thread)
    if not grant.granted and grant.failed:
        # 誰にも付与できなかった場合は、成功として見せない
        await send_error_message(ctx, describe_grant(grant) + note)
        return
    await send_private_reply(
        ctx,
        create_success_embed(
            title="イベントロールメンバー追加完了",
            description=describe_grant(grant) + note,
            イベントチャンネル=event_channel.mention,
            ロール=role.name,
            追加人数=len(grant.granted),
        ),
    )
    logger.info(
        f"Added {len(grant.granted)} members to event role {role.name} "
        f"(channel: {event_channel.name}) by {ctx.user}"
    )

    if grant.granted:
        await post_channel_record(
            event_channel,
            build_members_added_embed(actor=ctx.user, role=role, members=grant.granted),
            mention_users=grant.granted,
            mention_label="新しい参加者",
        )


# ==================== コマンド登録 ====================


def setup(tree: app_commands.CommandTree):
    """イベントチャンネル関連のコマンドを登録する

    デコレーターの順序（重要）:
    1. @command_meta() - メタデータの登録
    2. @tree.command() - コマンドの登録
    3. @app_commands.describe() - パラメータの説明
    """

    @command_meta(
        category="イベントチャンネル管理",
        icon="📅",
        short_description="イベント用のチャンネルとロールを作成",
        restrictions="• どのチャンネル・スレッドからでも実行可能",
        examples=[
            "`/create_event_channel channel_name:おでん会`",
            "`/create_event_channel channel_name:忘年会 members:@user1 @user2`",
        ],
    )
    @tree.command(
        name="create_event_channel",
        description="新しいイベントチャンネルを作成します",
    )
    @app_commands.describe(
        channel_name="作成するイベントチャンネル名",
        members="ロールに追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
    )
    async def create_event_channel(
        ctx: discord.Interaction, channel_name: str, members: str | None = None
    ):
        await create_event_channel_impl(ctx, channel_name, members)

    @command_meta(
        category="イベントチャンネル管理",
        icon="📅",
        short_description="イベントチャンネルをアーカイブに移動",
        restrictions="• channel_name省略時はイベントカテゴリー内（スレッド可）で実行",
        examples=[
            "`/archive_event_channel` (実行チャンネルをアーカイブ)",
            "`/archive_event_channel channel_name:#e001-おでん会`",
        ],
    )
    @tree.command(
        name="archive_event_channel",
        description="イベントチャンネルをアーカイブします",
    )
    @app_commands.describe(
        channel_name="アーカイブするイベントチャンネル（メンション形式、省略時はコマンド実行チャンネル）"
    )
    async def archive_event_channel(
        ctx: discord.Interaction, channel_name: discord.TextChannel | None = None
    ):
        await archive_event_channel_impl(ctx, channel_name)

    @command_meta(
        category="イベントチャンネル管理",
        icon="📅",
        short_description="アーカイブからイベントチャンネルを復元",
        restrictions="• channel_name省略時はアーカイブカテゴリー内（スレッド可）で実行",
        examples=[
            "`/restore_event_channel` (実行チャンネルを復元)",
            "`/restore_event_channel channel_name:#e001-おでん会`",
        ],
    )
    @tree.command(
        name="restore_event_channel",
        description="アーカイブされたイベントチャンネルをイベントカテゴリーに戻します",
    )
    @app_commands.describe(
        channel_name="復元するイベントチャンネル（メンション形式、デフォルトはコマンド実行チャンネル）"
    )
    async def restore_event_channel(
        ctx: discord.Interaction, channel_name: discord.TextChannel | None = None
    ):
        await restore_event_channel_impl(ctx, channel_name)

    @command_meta(
        category="ロール管理",
        icon="👥",
        short_description="イベントロールにメンバーを追加",
        restrictions="• 一部ロール以外のみ対象",
        examples=[
            "`/add_event_role_member members:@user1 @user2`",
            "`/add_event_role_member members:@user1 role_name:@e001`",
        ],
    )
    @tree.command(
        name="add_event_role_member",
        description="イベントチャンネルに紐づくロールにメンバーを追加します",
    )
    @app_commands.describe(
        members="追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
        role_name="対象のロール（@ロール形式で指定。例: @e001. 省略時は実行チャンネルのロール）",
    )
    async def add_event_role_member(
        ctx: discord.Interaction, members: str, role_name: str | None = None
    ):
        await add_event_role_member_impl(ctx, members, role_name)
