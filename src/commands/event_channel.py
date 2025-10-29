"""イベントチャンネル管理コマンド"""

from logging import getLogger

import discord
from discord import app_commands

from ..utils.channel_utils import get_next_event_index, validate_category_exists
from ..utils.event_config import EventChannelConfig
from ..utils.message_utils import (
    create_success_embed,
    handle_command_error,
    send_error_message,
)
from ..utils.validation_utils import (
    get_channel_by_name,
    parse_member_mentions,
    parse_role_mention,
    validate_channel_in_category,
    validate_channel_restriction,
    validate_role_safety,
)

logger = getLogger(__name__)


async def create_event_channel(
    ctx: discord.Interaction,
    channel_name: str,
    members: str = None,
):
    """イベントチャンネルを作成するコマンド"""

    # 環境変数を一括取得
    config = await EventChannelConfig.load(ctx)
    if not config:
        return

    # コマンド実行チャンネルの確認
    if not await validate_channel_restriction(
        ctx, config.event_request_channel_name, must_be_in=True
    ):
        return

    # カテゴリーの存在確認
    guild = ctx.guild
    category_channel = await validate_category_exists(
        ctx, guild, config.event_category_name
    )
    if not category_channel:
        return

    # メンバーが指定されている場合、メンションから抽出
    member_objects = []
    if members:
        parsed_members = await parse_member_mentions(ctx, members, guild)
        if parsed_members is None:
            return
        member_objects = parsed_members

    try:
        # 次のインデックス番号を取得
        next_index = get_next_event_index(
            guild, config.event_category_name, config.archive_event_category_name
        )

        # チャンネル名を {index}-{name} の形式で構築
        formatted_channel_name = f"{next_index}-{channel_name}"

        # チャンネルを作成
        channel = await guild.create_text_channel(
            name=formatted_channel_name, category=category_channel
        )

        # 同じ名前のロールを作成
        role = await guild.create_role(
            name=formatted_channel_name,
            mentionable=True,
        )

        # 指定されたメンバーにロールを付与
        if member_objects:
            for member in member_objects:
                await member.add_roles(role)

        # 成功メッセージ
        description_parts = [f"{channel.mention} と {role.mention} を作成しました"]

        if member_objects:
            member_mentions_str = ", ".join([m.mention for m in member_objects])
            description_parts.append(
                f"\n以下のメンバーにロールを付与しました:\n{member_mentions_str}"
            )

        embed = create_success_embed(
            title="イベントチャンネル作成完了",
            description="".join(description_parts),
            チャンネル名=formatted_channel_name,
            インデックス=next_index,
            ロール付与人数=len(member_objects) if member_objects else 0,
        )

        await ctx.response.send_message(embed=embed)
        logger.info(
            f"Created channel: {formatted_channel_name} (index: {next_index}) and role "
            f"with {len(member_objects)} members by {ctx.user}"
        )

    except Exception as e:
        logger.error(f"Error creating channel: {e}")
        await handle_command_error(ctx, e, "チャンネルの作成")


async def archive_event_channel(
    ctx: discord.Interaction,
    channel_name: str = None,
):
    """イベントチャンネルをアーカイブするコマンド"""

    # 環境変数を一括取得
    config = await EventChannelConfig.load(ctx)
    if not config:
        return

    guild = ctx.guild

    # アーカイブ先カテゴリーの存在確認
    archive_category_channel = await validate_category_exists(
        ctx, guild, config.archive_event_category_name
    )
    if not archive_category_channel:
        return

    # 移動するチャンネルを特定
    if channel_name:
        channel = await get_channel_by_name(ctx, guild, channel_name)
        if not channel:
            return
    else:
        # channel_name省略時は、EVENT_REQUEST_CHANNEL以外で実行
        if not await validate_channel_restriction(
            ctx, config.event_request_channel_name, must_be_in=False
        ):
            return
        channel = ctx.channel

    # チャンネルがイベントカテゴリーに属しているか確認
    if not await validate_channel_in_category(ctx, channel, config.event_category_name):
        return

    try:
        await channel.edit(category=archive_category_channel)

        # 成功メッセージ
        embed = create_success_embed(
            title="イベントチャンネルアーカイブ完了",
            description=f"{channel.mention} をアーカイブしました",
            チャンネル名=channel.name,
        )

        await ctx.response.send_message(embed=embed)
        logger.info(f"Archived channel: {channel.name} by {ctx.user}")

    except Exception as e:
        logger.error(f"Error archiving channel: {e}")
        await handle_command_error(ctx, e, "チャンネルのアーカイブ")


async def restore_event_channel(
    ctx: discord.Interaction,
    channel_name: str = None,
):
    """アーカイブされたイベントチャンネルをイベントカテゴリーに戻すコマンド"""

    # 環境変数を一括取得
    config = await EventChannelConfig.load(ctx)
    if not config:
        return

    guild = ctx.guild

    # イベントカテゴリーの存在確認
    event_category_channel = await validate_category_exists(
        ctx, guild, config.event_category_name
    )
    if not event_category_channel:
        return

    # 移動するチャンネルを特定
    if channel_name:
        # channel_name指定時は任意の場所で実行可能
        channel = await get_channel_by_name(ctx, guild, channel_name)
        if not channel:
            return
    else:
        # channel_name省略時は、アーカイブカテゴリー内でのみ実行可能
        channel = ctx.channel
        if not await validate_channel_in_category(
            ctx, channel, config.archive_event_category_name
        ):
            return

    # チャンネルがアーカイブカテゴリーに属しているか確認（channel_name指定時）
    if channel_name and not await validate_channel_in_category(
        ctx, channel, config.archive_event_category_name
    ):
        return

    try:
        await channel.edit(category=event_category_channel)

        # 成功メッセージ
        embed = create_success_embed(
            title="イベントチャンネル復元完了",
            description=f"{channel.mention} をイベントカテゴリーに戻しました",
            チャンネル名=channel.name,
        )

        await ctx.response.send_message(embed=embed)
        logger.info(f"Restored channel: {channel.name} by {ctx.user}")

    except Exception as e:
        logger.error(f"Error restoring channel: {e}")
        await handle_command_error(ctx, e, "チャンネルの復元")


async def add_event_role_member(
    ctx: discord.Interaction,
    members: str,
    role_name: str = None,
):
    """イベントチャンネルに紐づくロールにメンバーを追加するコマンド

    実行可能なロールはEVENT_CATEGORY_NAMEカテゴリのチャンネルに対応するものだけ
    role_nameを省略した場合は、コマンド実行チャンネルと同名のロールを使用
    """

    # 環境変数を一括取得
    config = await EventChannelConfig.load(ctx)
    if not config:
        return

    guild = ctx.guild

    # カテゴリーの存在確認
    event_category = await validate_category_exists(
        ctx, guild, config.event_category_name
    )
    if not event_category:
        return

    # role_nameが省略された場合は実行チャンネル名を使用
    if role_name is None:
        # コマンド実行チャンネルがEVENT_CATEGORY_NAMEカテゴリーに属しているか確認
        if not await validate_channel_in_category(
            ctx, ctx.channel, config.event_category_name
        ):
            return
        role_name = ctx.channel.name
        # ロールを名前で検索
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            await send_error_message(ctx, f"ロール `{role_name}` が見つかりません。")
            return
    else:
        # role_nameが指定された場合、パース関数でロールを取得
        role = await parse_role_mention(ctx, role_name, guild)
        if not role:
            return
        role_name = role.name

    # ロールの安全性チェック
    if not await validate_role_safety(ctx, role):
        return

    # 同名のチャンネルがEVENT_CATEGORY_NAMEカテゴリーに存在するか確認
    event_channel = discord.utils.get(event_category.text_channels, name=role_name)
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

    try:
        # ロールを追加
        added_members = []
        already_has_role = []

        for member in member_objects:
            if role in member.roles:
                already_has_role.append(member)
            else:
                await member.add_roles(role)
                added_members.append(member)

        # 成功メッセージ
        description_parts = []

        if added_members:
            member_mentions_str = ", ".join([m.mention for m in added_members])
            description_parts.append(
                f"{role.mention} に以下のメンバーを追加しました:\n{member_mentions_str}"
            )

        if already_has_role:
            member_mentions_str = ", ".join([m.mention for m in already_has_role])
            description_parts.append(
                f"\n以下のメンバーは既にロールを持っています:\n{member_mentions_str}"
            )

        embed = create_success_embed(
            title="イベントロールメンバー追加完了",
            description="\n".join(description_parts),
            イベントチャンネル=event_channel.mention,
            ロール=role.name,
            追加人数=len(added_members),
        )

        await ctx.response.send_message(embed=embed)
        logger.info(
            f"Added {len(added_members)} members to event role {role.name} "
            f"(channel: {event_channel.name}) by {ctx.user}"
        )

    except discord.Forbidden:
        await send_error_message(
            ctx, f"Botに {role.mention} を付与する権限がありません。"
        )
    except Exception as e:
        logger.error(f"Error adding event role members: {e}")
        await handle_command_error(ctx, e, "イベントロールメンバーの追加")


def setup(tree: app_commands.CommandTree):
    """イベントチャンネル関連のコマンドを登録する"""

    @tree.command(
        name="create_event_channel", description="新しいイベントチャンネルを作成します"
    )
    @app_commands.describe(
        channel_name="作成するイベントチャンネル名",
        members="ロールに追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
    )
    async def create_event_channel_cmd(
        ctx: discord.Interaction, channel_name: str, members: str = None
    ):
        await create_event_channel(ctx, channel_name, members)

    @tree.command(
        name="archive_event_channel", description="イベントチャンネルをアーカイブします"
    )
    @app_commands.describe(
        channel_name="アーカイブするイベントチャンネル名(デフォルトはコマンド実行チャンネル)"
    )
    async def archive_event_channel_cmd(
        ctx: discord.Interaction, channel_name: str = None
    ):
        await archive_event_channel(ctx, channel_name)

    @tree.command(
        name="restore_event_channel",
        description="アーカイブされたイベントチャンネルをイベントカテゴリーに戻します",
    )
    @app_commands.describe(
        channel_name="復元するイベントチャンネル名(デフォルトはコマンド実行チャンネル)"
    )
    async def restore_event_channel_cmd(
        ctx: discord.Interaction, channel_name: str = None
    ):
        await restore_event_channel(ctx, channel_name)

    @tree.command(
        name="add_event_role_member",
        description="イベントチャンネルに紐づくロールにメンバーを追加します",
    )
    @app_commands.describe(
        members="追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
        role_name="対象のロール（@ロール形式で指定。例: @1-event. 省略時は実行チャンネルのロール）",
    )
    async def add_event_role_member_cmd(
        ctx: discord.Interaction, members: str, role_name: str = None
    ):
        await add_event_role_member(ctx, members, role_name)
