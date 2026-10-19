"""クラブ・イベント・プロジェクトのチャンネル管理コマンド"""

from collections.abc import Sequence
from logging import getLogger

import discord
from discord import app_commands

from ..utils.capacity import check_move_capacity
from ..utils.channel_config import ChannelConfig
from ..utils.channel_order import move_channel
from ..utils.channel_utils import (
    get_next_number,
    resolve_target_text_channel_or_error,
    thread_target_note,
    validate_category_exists,
)
from ..utils.command_metadata import command_meta
from ..utils.creation import Created, Rejected, create_channel_with_role
from ..utils.kinds import KINDS, Kind
from ..utils.linking import (
    Linked,
    NotLinked,
    collect_kind_categories,
    explain_not_linked,
    link_channel,
    link_role,
    locate_channel,
)
from ..utils.message_utils import (
    create_success_embed,
    handle_command_error,
    report_creation_problem,
    send_error_message,
    send_private_reply,
)
from ..utils.numbering import NUMBERS_EXHAUSTED
from ..utils.records import (
    build_archive_notice_embed,
    build_creation_embed,
    build_members_added_embed,
    build_members_removed_embed,
    build_restored_embed,
    delete_record,
    post_channel_record,
)
from ..utils.role_utils import (
    describe_grant,
    describe_revoke,
    grant_role,
    revoke_role,
    with_creator,
)
from ..utils.validation_utils import parse_member_mentions, validate_role_safety

logger = getLogger(__name__)

PERMISSION_HELP = (
    "サーバー管理者に、`{category}`, `{archive}`のカテゴリに「権限の管理」"
    "権限がInTech Botのみに付与されているか確認してください。"
)

KIND_CHOICES = [app_commands.Choice(name=kind.label, value=kind.key) for kind in KINDS]


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

    own_name, _ = config.category_names(kind)
    category_channel = await validate_category_exists(ctx, guild, own_name)
    if not category_channel:
        return

    member_objects: list[discord.Member] = []
    if members:
        parsed_members = await parse_member_mentions(ctx, members, guild)
        if parsed_members is None:
            return
        member_objects = parsed_members

    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    def decide_name(guild: discord.Guild, category: discord.CategoryChannel) -> str | Rejected:
        # 採番はLockの中で行い、並行した作成で番号が重ならないようにする
        number = get_next_number(guild, kind, config.category_names(kind))
        if number is None:
            return Rejected(NUMBERS_EXHAUSTED)
        return kind.channel_name(number, channel_name)

    try:
        outcome = await create_channel_with_role(
            guild,
            category_channel,
            decide_name=decide_name,
            role_name_for=lambda channel: kind.role_name(channel.name),
            role_kind=kind.key,
        )
    except Exception as e:
        await handle_command_error(ctx, e, f"{kind.label}チャンネルの作成")
        return

    if not isinstance(outcome, Created):
        await report_creation_problem(ctx, outcome, f"{kind.label}チャンネルの作成")
        return

    channel, role = outcome.channel, outcome.role
    # 立てた人は、その時点で参加者になる
    grant = await grant_role(with_creator(member_objects, ctx.user), role)

    description = f"{channel.mention} と {role.mention} を作成しました"
    grant_description = describe_grant(grant)
    if grant_description:
        description += f"\n{grant_description}"
    await send_private_reply(
        ctx,
        create_success_embed(
            title=f"{kind.label}チャンネル作成完了",
            description=description,
            チャンネル名=channel.name,
            ロール付与人数=len(grant.granted),
        ),
    )
    logger.info(
        f"Created {kind.key} channel: {channel.name} and role {role.name} "
        f"with {len(grant.granted)} members by {ctx.user}"
    )

    await post_channel_record(
        channel,
        build_creation_embed(
            kind=kind.label,
            actor=ctx.user,
            channel=channel,
            role=role,
            members=grant.granted,
            failed_members=grant.failed,
            join_command="/add_role_members",
        ),
        mention_users=grant.granted,
        mention_label="参加者",
    )


async def _resolve_channel_to_move(
    ctx: discord.Interaction,
    channel: discord.TextChannel | None,
    *,
    archived: bool,
) -> tuple[ChannelConfig, discord.TextChannel, Kind, bool] | None:
    """アーカイブ・復元の対象を決める。archivedは対象が今アーカイブ中であるべきか"""
    config = await ChannelConfig.load(ctx)
    if not config:
        return None

    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return None

    via_thread = False
    if channel is None:
        channel, via_thread = await resolve_target_text_channel_or_error(ctx)
        if channel is None:
            return None

    categories, missing = _kind_categories(guild, config)
    located = locate_channel(channel, categories)
    if isinstance(located, NotLinked):
        await send_error_message(ctx, explain_not_linked(located, missing))
        return None
    if located.archived != archived:
        state = "アーカイブされていません" if archived else "既にアーカイブされています"
        await send_error_message(ctx, f"{channel.mention} は{state}。")
        return None
    return config, channel, located.kind, via_thread


async def archive_channel_impl(
    ctx: discord.Interaction,
    channel: discord.TextChannel | None = None,
):
    """チャンネルをその種類のアーカイブカテゴリへ移す

    Args:
        ctx: Discord Interaction
        channel: アーカイブするチャンネル（省略時は実行チャンネル）
    """
    resolved = await _resolve_channel_to_move(ctx, channel, archived=False)
    if resolved is None:
        return
    config, target, kind, via_thread = resolved
    assert ctx.guild is not None

    own_name, archive_name = config.category_names(kind)
    archive_category = await validate_category_exists(ctx, ctx.guild, archive_name)
    if not archive_category:
        return

    capacity_reason = check_move_capacity(
        destination_category_channels=len(archive_category.channels)
    )
    if capacity_reason is not None:
        await send_error_message(ctx, capacity_reason)
        return

    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    # アーカイブ先ではbotが送信できない可能性があるため、移動の前に記録を残す
    notice = await post_channel_record(
        target,
        build_archive_notice_embed(actor=ctx.user, restore_command="/restore_channel"),
    )

    try:
        await move_channel(target, archive_category, kind)
    except Exception as e:
        notice_left = notice is not None and not await delete_record(notice)
        await handle_command_error(
            ctx,
            e,
            "チャンネルのアーカイブ",
            custom_help_texts={
                discord.Forbidden: PERMISSION_HELP.format(category=own_name, archive=archive_name)
            },
        )
        if notice_left:
            await send_error_message(
                ctx,
                f"{target.mention} に投稿した「アーカイブしました」の記録を消せませんでした。"
                "アーカイブはされていないので、記録を手で消してください。",
            )
        return

    await send_private_reply(
        ctx,
        create_success_embed(
            title=f"{kind.label}チャンネルアーカイブ完了",
            description=(
                f"{target.mention} をアーカイブしました{thread_target_note(target, via_thread)}"
            ),
            チャンネル名=target.name,
        ),
    )
    logger.info(f"Archived {kind.key} channel: {target.name} by {ctx.user}")


async def restore_channel_impl(
    ctx: discord.Interaction,
    channel: discord.TextChannel | None = None,
):
    """アーカイブされたチャンネルを、その種類のカテゴリへ戻す

    Args:
        ctx: Discord Interaction
        channel: 復元するチャンネル（省略時は実行チャンネル）
    """
    resolved = await _resolve_channel_to_move(ctx, channel, archived=True)
    if resolved is None:
        return
    config, target, kind, via_thread = resolved
    assert ctx.guild is not None

    own_name, archive_name = config.category_names(kind)
    own_category = await validate_category_exists(ctx, ctx.guild, own_name)
    if not own_category:
        return

    capacity_reason = check_move_capacity(destination_category_channels=len(own_category.channels))
    if capacity_reason is not None:
        await send_error_message(ctx, capacity_reason)
        return

    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    try:
        await move_channel(target, own_category, kind)
    except Exception as e:
        await handle_command_error(
            ctx,
            e,
            "チャンネルの復元",
            custom_help_texts={
                discord.Forbidden: PERMISSION_HELP.format(category=own_name, archive=archive_name)
            },
        )
        return

    await send_private_reply(
        ctx,
        create_success_embed(
            title=f"{kind.label}チャンネル復元完了",
            description=(
                f"{target.mention} を復元しました{thread_target_note(target, via_thread)}"
            ),
            チャンネル名=target.name,
        ),
    )
    logger.info(f"Restored {kind.key} channel: {target.name} by {ctx.user}")

    await post_channel_record(target, build_restored_embed(actor=ctx.user, channel=target))


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

    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    grant = await grant_role(member_objects, linked.role)

    note = thread_target_note(linked.channel, via_thread)
    if not grant.granted and grant.failed:
        # 誰にも付与できなかった場合は、成功として見せない
        await send_error_message(ctx, describe_grant(grant) + note)
        return
    await send_private_reply(
        ctx,
        create_success_embed(
            title="参加者の追加完了",
            description=describe_grant(grant) + note,
            チャンネル=linked.channel.mention,
            ロール=linked.role.name,
            追加人数=len(grant.granted),
        ),
    )
    logger.info(
        f"Added {len(grant.granted)} members to role {linked.role.name} "
        f"(channel: {linked.channel.name}) by {ctx.user}"
    )

    if grant.granted:
        await post_channel_record(
            linked.channel,
            build_members_added_embed(actor=ctx.user, role=linked.role, members=grant.granted),
            mention_users=grant.granted,
            mention_label="新しい参加者",
        )


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

    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    revoke = await revoke_role(member_objects, linked.role)

    note = thread_target_note(linked.channel, via_thread)
    if not revoke.revoked and revoke.failed:
        # 誰からも外せなかった場合は、成功として見せない
        await send_error_message(ctx, describe_revoke(revoke) + note)
        return
    await send_private_reply(
        ctx,
        create_success_embed(
            title="参加者の削除完了",
            description=describe_revoke(revoke) + note,
            チャンネル=linked.channel.mention,
            ロール=linked.role.name,
            削除人数=len(revoke.revoked),
        ),
    )
    logger.info(
        f"Removed {len(revoke.revoked)} members from role {linked.role.name} "
        f"(channel: {linked.channel.name}) by {ctx.user}"
    )

    if revoke.revoked:
        # 外された人には通知しない（mention_usersを渡さず、Embedの中にだけ書く）
        await post_channel_record(
            linked.channel,
            build_members_removed_embed(actor=ctx.user, role=linked.role, members=revoke.revoked),
        )


def _kind_of(key: str) -> Kind:
    return next(kind for kind in KINDS if kind.key == key)


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
        restrictions="• クラブ・イベント・プロジェクトのロールのみ対象（アーカイブ中も可）",
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
        role="対象のロール（例: @e001。省略時は実行チャンネルのロール）",
    )
    async def add_role_members(
        ctx: discord.Interaction, members: str, role: discord.Role | None = None
    ):
        await add_role_members_impl(ctx, members, role)

    @command_meta(
        category="ロール管理",
        icon="👥",
        short_description="チャンネルのロールから参加者を外す",
        restrictions="• クラブ・イベント・プロジェクトのロールのみ対象（アーカイブ中も可）",
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
        role="対象のロール（例: @e001。省略時は実行チャンネルのロール）",
    )
    async def remove_role_members(
        ctx: discord.Interaction, members: str, role: discord.Role | None = None
    ):
        await remove_role_members_impl(ctx, members, role)
