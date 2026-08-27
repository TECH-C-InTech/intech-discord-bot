"""プロジェクトチャンネル管理コマンド"""

from logging import getLogger
import re

import discord
from discord import app_commands

from ..utils.approval_decorator import require_approval
from ..utils.channel_config import ChannelConfig
from ..utils.channel_decorator import require_channel
from ..utils.channel_utils import (
    get_next_project_index,
    validate_category_exists,
)
from ..utils.command_metadata import command_meta
from ..utils.message_utils import (
    create_success_embed,
    handle_command_error,
    send_error_message,
)
from ..utils.validation_utils import (
    parse_member_mentions,
    parse_role_mention,
    validate_channel_in_category,
    validate_role_safety,
)

logger = getLogger(__name__)


# ==================== コマンド実装関数 ====================


async def create_project_channel_impl(
    ctx: discord.Interaction,
    channel_name: str,
    members: str | None = None,
):
    """プロジェクトチャンネルを作成する

    Args:
        ctx: Discord Interaction
        channel_name: 作成するプロジェクトチャンネル名
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

    category_channel = await validate_category_exists(ctx, guild, config.project_category_name)
    if not category_channel:
        return

    # メンバーが指定されている場合、メンションから抽出
    member_objects = []
    if members:
        parsed_members = await parse_member_mentions(ctx, members, guild)
        if parsed_members is None:
            return
        member_objects = parsed_members

    if not ctx.response.is_done():
        await ctx.response.defer(thinking=True)

    try:
        # 次のインデックス番号を取得
        next_index = get_next_project_index(
            guild,
            config.project_category_name,
            config.archive_project_category_name,
        )

        # チャンネル名を p{index:03d}-{name} の形式で構築（3桁0埋め）
        formatted_channel_name = f"p{next_index:03d}-{channel_name}"

        # チャンネルを作成
        channel = await guild.create_text_channel(
            name=formatted_channel_name, category=category_channel
        )

        # p{index}形式のロールを作成（3桁0埋め）
        role_name = f"p{next_index:03d}"
        role = await guild.create_role(
            name=role_name,
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
            title="プロジェクトチャンネル作成完了",
            description="".join(description_parts),
            チャンネル名=formatted_channel_name,
            インデックス=next_index,
            ロール付与人数=len(member_objects) if member_objects else 0,
        )

        # Interactionが既に応答済みの場合はfollowupを使用
        if ctx.response.is_done():
            await ctx.followup.send(embed=embed)
        else:
            await ctx.response.send_message(embed=embed)
        logger.info(
            f"Created channel: {formatted_channel_name} (index: {next_index}) and role "
            f"with {len(member_objects)} members by {ctx.user}"
        )

    except Exception as e:
        logger.error(f"Error creating channel: {e}", exc_info=True)
        await handle_command_error(ctx, e, "チャンネルの作成")


async def archive_project_channel_impl(
    ctx: discord.Interaction,
    channel_name: discord.TextChannel | None = None,
):
    """プロジェクトチャンネルをアーカイブする

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
        ctx, guild, config.archive_project_category_name
    )
    if not archive_category_channel:
        return

    # 移動するチャンネルを特定
    channel: discord.TextChannel | None = channel_name
    if channel is None:
        if not isinstance(ctx.channel, discord.TextChannel):
            await send_error_message(
                ctx,
                "このコマンドはテキストチャンネルでのみ実行できます。",
            )
            return
        channel = ctx.channel

    # チャンネルがプロジェクトカテゴリーに属しているか確認
    if not await validate_channel_in_category(ctx, channel, config.project_category_name):
        return

    if not ctx.response.is_done():
        await ctx.response.defer(thinking=True)

    try:
        await channel.edit(category=archive_category_channel, sync_permissions=True)

        # 成功メッセージ
        embed = create_success_embed(
            title="プロジェクトチャンネルアーカイブ完了",
            description=f"{channel.mention} をアーカイブしました",
            チャンネル名=channel.name,
        )

        # Interactionが既に応答済みの場合はfollowupを使用
        if ctx.response.is_done():
            await ctx.followup.send(embed=embed)
        else:
            await ctx.response.send_message(embed=embed)
        logger.info(f"Archived channel: {channel.name} by {ctx.user}")

    except Exception as e:
        logger.error(f"Error archiving channel: {e}", exc_info=True)
        await handle_command_error(
            ctx,
            e,
            "チャンネルのアーカイブ",
            custom_help_texts={
                discord.Forbidden: (
                    f"サーバー管理者に、`{config.project_category_name}`, "
                    f"`{config.archive_project_category_name}`のカテゴリに「権限の管理」"
                    f"権限がInTech Botのみに付与されているか確認してください。"
                )
            },
        )


async def restore_project_channel_impl(
    ctx: discord.Interaction,
    channel_name: discord.TextChannel | None = None,
):
    """アーカイブされたプロジェクトチャンネルを復元する

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

    # プロジェクトカテゴリーの存在確認
    project_category_channel = await validate_category_exists(
        ctx, guild, config.project_category_name
    )
    if not project_category_channel:
        return

    # 移動するチャンネルを特定
    channel: discord.TextChannel | None = channel_name
    if channel is None:
        # channel_name省略時は、アーカイブカテゴリー内でのみ実行可能
        if not isinstance(ctx.channel, discord.TextChannel):
            await send_error_message(ctx, "このコマンドはテキストチャンネルでのみ実行できます。")
            return
        channel = ctx.channel

    if not await validate_channel_in_category(ctx, channel, config.archive_project_category_name):
        return

    if not ctx.response.is_done():
        await ctx.response.defer(thinking=True)

    try:
        await channel.edit(category=project_category_channel, sync_permissions=True)

        # 成功メッセージ
        embed = create_success_embed(
            title="プロジェクトチャンネル復元完了",
            description=f"{channel.mention} をプロジェクトカテゴリーに戻しました",
            チャンネル名=channel.name,
        )

        # Interactionが既に応答済みの場合はfollowupを使用
        if ctx.response.is_done():
            await ctx.followup.send(embed=embed)
        else:
            await ctx.response.send_message(embed=embed)
        logger.info(f"Restored channel: {channel.name} by {ctx.user}")

    except Exception as e:
        logger.error(f"Error restoring channel: {e}", exc_info=True)
        await handle_command_error(
            ctx,
            e,
            "チャンネルの復元",
            custom_help_texts={
                discord.Forbidden: (
                    f"サーバー管理者に、`{config.project_category_name}`, "
                    f"`{config.archive_project_category_name}`のカテゴリに「権限の管理」"
                    f"権限がInTech Botのみに付与されているか確認してください。"
                )
            },
        )


async def add_project_role_member_impl(
    ctx: discord.Interaction,
    members: str,
    role_name: str | None = None,
):
    """プロジェクトロールにメンバーを追加する

    実行可能なロールはPROJECT_CATEGORY_NAMEカテゴリのチャンネルに対応するものだけ

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
    project_category = await validate_category_exists(ctx, guild, config.project_category_name)
    if not project_category:
        return

    # role_nameが省略された場合は実行チャンネル名を使用
    if role_name is None:
        # コマンド実行チャンネルがPROJECT_CATEGORY_NAMEカテゴリーに属しているか確認
        if not isinstance(ctx.channel, discord.TextChannel):
            await send_error_message(ctx, "このコマンドはテキストチャンネルでのみ実行できます。")
            return
        if not await validate_channel_in_category(ctx, ctx.channel, config.project_category_name):
            return
        channel_name = ctx.channel.name
        # チャンネル名からindexを抽出して、p{index}形式のロールを検索
        # チャンネル名: p001-xxx -> index: 001
        match = re.match(r"^p(\d{3})-", channel_name)
        if not match:
            await send_error_message(
                ctx, "このチャンネルはプロジェクトチャンネルの形式（p001-xxx）ではありません。"
            )
            return
        channel_index = int(match.group(1))
        role_name_to_find = f"p{channel_index:03d}"
        role = discord.utils.get(guild.roles, name=role_name_to_find)
        if not role:
            await send_error_message(ctx, f"ロール `{role_name_to_find}` が見つかりません。")
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

    # ロール名から数字部分を抽出（p001 -> 1）
    # role_nameはこの時点で必ず文字列
    assert role_name is not None
    role_pattern = re.compile(r"^p(\d{3})$")
    role_match = role_pattern.match(role_name)
    if not role_match:
        await send_error_message(
            ctx,
            f"ロール {role.mention} はプロジェクトロールの形式（p001形式）ではありません。",
        )
        return

    role_index = int(role_match.group(1))

    # 同名のチャンネルがPROJECT_CATEGORY_NAMEカテゴリーに存在するか確認
    # p{index:03d}-で始まるチャンネルを検索（3桁0埋め）
    project_channel = None
    for ch_name in project_category.text_channels:
        if ch_name.name.startswith(f"p{role_index:03d}-"):
            project_channel = ch_name
            break

    if not project_channel:
        await send_error_message(
            ctx,
            f"ロール {role.mention} に対応するプロジェクトチャンネルが見つかりません。\n"
            f"このコマンドは{config.project_category_name}カテゴリー内のチャンネルに対応するロールのみ操作可能です。",
        )
        return

    # メンバーをメンションから抽出
    member_objects = await parse_member_mentions(ctx, members, guild)
    if member_objects is None:
        return

    # 応答を保留
    if not ctx.response.is_done():
        await ctx.response.defer(thinking=True)

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
            title="プロジェクトロールメンバー追加完了",
            description="\n".join(description_parts),
            プロジェクトチャンネル=project_channel.mention,
            ロール=role.name,
            追加人数=len(added_members),
        )

        # 結果をfollowupで送信
        await ctx.followup.send(embed=embed)
        logger.info(
            f"Added {len(added_members)} members to project role {role.name} "
            f"(channel: {project_channel.name}) by {ctx.user}"
        )

    except discord.Forbidden:
        await send_error_message(ctx, f"Botに {role.mention} を付与する権限がありません。")
    except Exception as e:
        logger.error(f"Error adding project role members: {e}", exc_info=True)
        await handle_command_error(ctx, e, "プロジェクトロールメンバーの追加")


# ==================== コマンド登録 ====================


def setup(tree: app_commands.CommandTree):
    """プロジェクトチャンネル関連のコマンドを登録する

    デコレーターの順序（重要）:
    1. @command_meta() - メタデータの登録
    2. @tree.command() - コマンドの登録
    3. @require_channel() - チャンネル制限（オプション）
    4. @require_approval() - 承認ミドルウェア（オプション）
    5. @app_commands.describe() - パラメータの説明
    """

    @command_meta(
        category="プロジェクトチャンネル管理",
        icon="🚀",
        short_description="プロジェクト用のチャンネルとロールを作成",
        restrictions="• プロジェクトリクエストチャンネルでのみ実行可能",
        examples=[
            "`/create_project_channel channel_name:ハッカソン`",
            "`/create_project_channel channel_name:discordbot members:@user1 @user2`",
        ],
    )
    @tree.command(
        name="create_project_channel",
        description="新しいプロジェクトチャンネルを作成します",
    )
    @require_channel(channel_name_from_config="project_request_channel_name", must_be_in=True)
    @require_approval(description="新しいプロジェクトチャンネルを作成します")
    @app_commands.describe(
        channel_name="作成するプロジェクトチャンネル名",
        members="ロールに追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
    )
    async def create_project_channel(
        ctx: discord.Interaction, channel_name: str, members: str | None = None
    ):
        await create_project_channel_impl(ctx, channel_name, members)

    @command_meta(
        category="プロジェクトチャンネル管理",
        icon="🚀",
        short_description="プロジェクトチャンネルをアーカイブに移動",
        restrictions="• channel_name省略時はプロジェクトカテゴリー内で実行",
        examples=[
            "`/archive_project_channel` (実行チャンネルをアーカイブ)",
            "`/archive_project_channel channel_name:#p001-ハッカソン`",
        ],
    )
    @tree.command(
        name="archive_project_channel",
        description="プロジェクトチャンネルをアーカイブします",
    )
    @app_commands.describe(
        channel_name="アーカイブするプロジェクトチャンネル（メンション形式、省略時はコマンド実行チャンネル）"
    )
    async def archive_project_channel(
        ctx: discord.Interaction, channel_name: discord.TextChannel | None = None
    ):
        await archive_project_channel_impl(ctx, channel_name)

    @command_meta(
        category="プロジェクトチャンネル管理",
        icon="🚀",
        short_description="アーカイブからプロジェクトチャンネルを復元",
        restrictions="• アーカイブカテゴリー内のチャンネルでのみ実行可能",
        examples=[
            "`/restore_project_channel` (実行チャンネルを復元)",
            "`/restore_project_channel channel_name:#p001-ハッカソン`",
        ],
    )
    @tree.command(
        name="restore_project_channel",
        description="アーカイブされたプロジェクトチャンネルをプロジェクトカテゴリーに戻します",
    )
    @app_commands.describe(
        channel_name="復元するプロジェクトチャンネル（メンション形式、デフォルトはコマンド実行チャンネル）"
    )
    async def restore_project_channel(
        ctx: discord.Interaction, channel_name: discord.TextChannel | None = None
    ):
        await restore_project_channel_impl(ctx, channel_name)

    @command_meta(
        category="ロール管理",
        icon="👥",
        short_description="プロジェクトロールにメンバーを追加",
        restrictions="• 一部ロール以外のみ対象",
        examples=[
            "`/add_project_role_member members:@user1 @user2`",
            "`/add_project_role_member members:@user1 role_name:@p001`",
        ],
    )
    @tree.command(
        name="add_project_role_member",
        description="プロジェクトチャンネルに紐づくロールにメンバーを追加します",
    )
    @app_commands.describe(
        members="追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
        role_name="対象のロール（@ロール形式で指定。例: @p001. 省略時は実行チャンネルのロール）",
    )
    async def add_project_role_member(
        ctx: discord.Interaction, members: str, role_name: str | None = None
    ):
        await add_project_role_member_impl(ctx, members, role_name)
