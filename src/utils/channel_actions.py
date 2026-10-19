"""クラブ・イベント・プロジェクトの操作の本体

スラッシュコマンドとパネルのボタン・フォームの両方から呼ぶ。
対象のチャンネル・ロールと参加者は呼び出し側で決めて渡す。
本人への返信、チャンネル内の記録、ピン留めのパネルの書き換えまでをここで行う。
"""

from collections.abc import Sequence
from logging import getLogger

import discord

from .capacity import check_move_capacity
from .channel_config import ChannelConfig
from .channel_order import move_channel
from .channel_utils import get_next_number, thread_target_note, validate_category_exists
from .creation import Created, Rejected, create_channel_with_role
from .kinds import Kind
from .linking import (
    Linked,
    NotLinked,
    collect_kind_categories,
    explain_not_linked,
    locate_channel,
)
from .message_utils import (
    create_success_embed,
    handle_command_error,
    report_creation_problem,
    send_error_message,
    send_private_reply,
)
from .numbering import NUMBERS_EXHAUSTED
from .panel import place_panel, refresh_channel_panel, refresh_panel
from .records import (
    build_archive_notice_embed,
    build_creation_embed,
    build_joined_embed,
    build_left_embed,
    build_members_added_embed,
    build_members_removed_embed,
    build_restored_embed,
    delete_record,
    post_channel_record,
)
from .role_utils import (
    ROLE_FAILURE_HELP,
    describe_grant,
    describe_revoke,
    grant_role,
    revoke_role,
    with_creator,
)

logger = getLogger(__name__)


async def join(ctx: discord.Interaction, linked: Linked) -> None:
    """押した本人を参加者にする。本人の操作なので記録は通知しない"""
    user = ctx.user
    assert isinstance(user, discord.Member)
    if linked.role in user.roles:
        await send_error_message(ctx, f"{linked.channel.mention} にはすでに参加しています。")
        return
    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    grant = await grant_role([user], linked.role)
    if not grant.granted:
        await send_error_message(
            ctx, f"{linked.channel.mention} に参加できませんでした。", help_text=ROLE_FAILURE_HELP
        )
        return
    await send_private_reply(
        ctx,
        create_success_embed(
            title="参加しました",
            description=(
                f"{linked.channel.mention} の参加者になりました。"
                f"{linked.role.mention} のメンションが届きます"
            ),
        ),
    )
    logger.info(f"{user} joined role {linked.role.name}")
    await post_channel_record(linked.channel, build_joined_embed(member=user, role=linked.role))
    await refresh_panel(linked.channel, linked.role, archived=linked.archived, joined=[user])


async def leave(ctx: discord.Interaction, linked: Linked) -> None:
    """押した本人を参加者から外す。本人の操作なので記録は通知しない"""
    user = ctx.user
    assert isinstance(user, discord.Member)
    if linked.role not in user.roles:
        await send_error_message(ctx, f"{linked.channel.mention} には参加していません。")
        return
    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    revoke = await revoke_role([user], linked.role)
    if not revoke.revoked:
        await send_error_message(
            ctx, f"{linked.channel.mention} から抜けられませんでした。", help_text=ROLE_FAILURE_HELP
        )
        return
    await send_private_reply(
        ctx,
        create_success_embed(
            title="抜けました", description=f"{linked.channel.mention} の参加者から抜けました"
        ),
    )
    logger.info(f"{user} left role {linked.role.name}")
    await post_channel_record(linked.channel, build_left_embed(member=user, role=linked.role))
    await refresh_panel(linked.channel, linked.role, archived=linked.archived, left=[user])


async def add_participants(
    ctx: discord.Interaction,
    linked: Linked,
    members: Sequence[discord.Member],
    *,
    via_thread: bool = False,
) -> None:
    """ロールに参加者を加える。加えられた人には記録で通知する

    Args:
        ctx: Discord Interaction
        linked: 加えるチャンネルとロール
        members: 加えるメンバー
        via_thread: スレッドから実行して親チャンネルを選んだか
    """
    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    grant = await grant_role(members, linked.role)

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
        await refresh_panel(
            linked.channel, linked.role, archived=linked.archived, joined=grant.granted
        )


async def remove_participants(
    ctx: discord.Interaction,
    linked: Linked,
    members: Sequence[discord.Member],
    *,
    via_thread: bool = False,
) -> None:
    """ロールから参加者を外す。外された人には通知しない

    Args:
        ctx: Discord Interaction
        linked: 外すチャンネルとロール
        members: 外すメンバー
        via_thread: スレッドから実行して親チャンネルを選んだか
    """
    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    revoke = await revoke_role(members, linked.role)

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
        await refresh_panel(
            linked.channel, linked.role, archived=linked.archived, left=revoke.revoked
        )


# 移動時にカテゴリの権限をチャンネルに写すが、botが持っていない権限の許可・拒否は
# 書き込めない（botにそのチャンネルで「権限の管理」を個別に付与していれば書き込める）
PERMISSION_HELP = (
    "サーバー管理者に、`{category}`, `{archive}` カテゴリーの権限設定を確認してもらってください。"
    "botが持っていない権限の許可・拒否がカテゴリーに設定されていると、チャンネルを移動できません"
    "（botに「権限の管理」を個別に付与すると回避できます）。"
)


async def _locate_or_error(
    ctx: discord.Interaction,
    config: ChannelConfig,
    channel: discord.TextChannel,
    *,
    archived: bool,
) -> Kind | None:
    """チャンネルの種類を返す。archivedは今アーカイブ中であるべきか。違えば本人に理由を返す"""
    assert ctx.guild is not None
    categories, missing = collect_kind_categories(ctx.guild.categories, config.category_names)
    located = locate_channel(channel, categories)
    if isinstance(located, NotLinked):
        await send_error_message(ctx, explain_not_linked(located, missing))
        return None
    if located.archived != archived:
        state = "アーカイブされていません" if archived else "既にアーカイブされています"
        await send_error_message(ctx, f"{channel.mention} は{state}。")
        return None
    return located.kind


async def archive(
    ctx: discord.Interaction,
    config: ChannelConfig,
    channel: discord.TextChannel,
    *,
    via_thread: bool = False,
) -> None:
    """チャンネルをその種類のアーカイブカテゴリへ移す

    Args:
        ctx: Discord Interaction
        config: カテゴリの設定
        channel: アーカイブするチャンネル
        via_thread: スレッドから実行して親チャンネルを選んだか
    """
    kind = await _locate_or_error(ctx, config, channel, archived=False)
    if kind is None:
        return
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
        channel,
        build_archive_notice_embed(
            actor=ctx.user, restore_command="/restore_channel", restore_to=own_name
        ),
    )

    try:
        await move_channel(channel, archive_category, kind)
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
                f"{channel.mention} に投稿した「アーカイブしました」の記録を消せませんでした。"
                "アーカイブはされていないので、記録を手で消してください。",
            )
        return

    await send_private_reply(
        ctx,
        create_success_embed(
            title=f"{kind.label}チャンネルアーカイブ完了",
            description=(
                f"{channel.mention} をアーカイブしました{thread_target_note(channel, via_thread)}"
            ),
            チャンネル名=channel.name,
        ),
    )
    logger.info(f"Archived {kind.key} channel: {channel.name} by {ctx.user}")
    await refresh_channel_panel(ctx.guild, config.category_names, channel, archived=True)


async def restore(
    ctx: discord.Interaction,
    config: ChannelConfig,
    channel: discord.TextChannel,
    *,
    via_thread: bool = False,
) -> None:
    """アーカイブされたチャンネルを、その種類のカテゴリへ戻す

    Args:
        ctx: Discord Interaction
        config: カテゴリの設定
        channel: 復元するチャンネル
        via_thread: スレッドから実行して親チャンネルを選んだか
    """
    kind = await _locate_or_error(ctx, config, channel, archived=True)
    if kind is None:
        return
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
        await move_channel(channel, own_category, kind)
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
                f"{channel.mention} を復元しました{thread_target_note(channel, via_thread)}"
            ),
            チャンネル名=channel.name,
        ),
    )
    logger.info(f"Restored {kind.key} channel: {channel.name} by {ctx.user}")

    await post_channel_record(channel, build_restored_embed(actor=ctx.user, channel=channel))
    await refresh_channel_panel(ctx.guild, config.category_names, channel, archived=False)


JOIN_GUIDE = (
    "参加したい人には、このチャンネルを伝えてください。チャンネルのピン留めから参加できます。"
)


async def create(
    ctx: discord.Interaction,
    config: ChannelConfig,
    kind: Kind,
    name: str,
    members: Sequence[discord.Member],
) -> None:
    """チャンネルとロールを作り、立てた人と members を参加者にして、パネルを置く

    Args:
        ctx: Discord Interaction
        config: カテゴリの設定
        kind: 作成する種類
        name: チャンネル名（番号は自動で付く）
        members: 立てた人のほかに参加者にするメンバー
    """
    guild = ctx.guild
    assert guild is not None
    own_name, _ = config.category_names(kind)
    category_channel = await validate_category_exists(ctx, guild, own_name)
    if not category_channel:
        return

    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    def decide_name(guild: discord.Guild, category: discord.CategoryChannel) -> str | Rejected:
        # 採番はLockの中で行い、並行した作成で番号が重ならないようにする
        number = get_next_number(guild, kind, config.category_names(kind))
        if number is None:
            return Rejected(NUMBERS_EXHAUSTED)
        return kind.channel_name(number, name)

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
    grant = await grant_role(with_creator(members, ctx.user), role)

    description = f"{channel.mention} と {role.mention} を作成しました"
    grant_description = describe_grant(grant)
    if grant_description:
        description += f"\n{grant_description}"
    description += f"\n{JOIN_GUIDE}"
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

    # 作成の記録（履歴）と、ピン留めのパネル（今の状態）は分ける
    await post_channel_record(
        channel,
        build_creation_embed(
            kind=kind.label,
            actor=ctx.user,
            channel=channel,
            role=role,
            members=grant.granted,
            failed_members=grant.failed,
        ),
        mention_users=grant.granted,
        mention_label="参加者",
    )
    await place_panel(channel, role, archived=False, joined=grant.granted)
