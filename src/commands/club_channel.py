"""クラブチャンネル管理コマンド"""

from logging import getLogger

import discord
from discord import app_commands

from ..utils.approval_decorator import require_approval
from ..utils.channel_decorator import require_channel
from ..utils.channel_utils import validate_category_exists
from ..utils.command_metadata import command_meta
from ..utils.event_config import EventChannelConfig
from ..utils.message_utils import (
    create_success_embed,
    handle_command_error,
    send_error_message,
)
from ..utils.validation_utils import (
    parse_member_mentions,
    parse_role_mention,
    validate_role_safety,
)

logger = getLogger(__name__)


# ==================== コマンド実装関数 ====================


async def create_club_channel_impl(
    ctx: discord.Interaction,
    channel_name: str,
    members: str | None = None,
):
    """クラブチャンネルを作成する

    Args:
        ctx: Discord Interaction
        channel_name: 作成するクラブチャンネル名
        members: ロールに追加するメンバー（メンション形式）
    """
    # 環境変数を一括取得
    config = await EventChannelConfig.load(ctx)
    if not config:
        return

    # カテゴリーの存在確認
    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return

    category_channel = await validate_category_exists(ctx, guild, config.club_category_name)
    if not category_channel:
        return

    # メンバーが指定されている場合、メンションから抽出
    member_objects = []
    if members:
        parsed_members = await parse_member_mentions(ctx, members, guild)
        if parsed_members is None:
            return
        member_objects = parsed_members

    # チャンネル名をそのまま使用
    formatted_channel_name = channel_name

    # カテゴリ内に同名のチャンネルが既に存在するかチェック
    channel_dict = {ch.name: ch for ch in category_channel.text_channels}
    existing_channel = channel_dict.get(formatted_channel_name)
    if existing_channel:
        await send_error_message(
            ctx,
            f"チャンネル `{formatted_channel_name}` は既に{config.club_category_name}カテゴリ内に存在します。\n"
            f"別の名前を使用してください。",
        )
        logger.warning(
            f"Channel creation failed: '{formatted_channel_name}' already exists "
            f"in category '{config.club_category_name}' (requested by {ctx.user})"
        )
        return

    try:
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
            title="クラブチャンネル作成完了",
            description="".join(description_parts),
            チャンネル名=formatted_channel_name,
            ロール付与人数=len(member_objects) if member_objects else 0,
        )

        # Interactionが既に応答済みの場合はfollowupを使用
        if ctx.response.is_done():
            await ctx.followup.send(embed=embed)
        else:
            await ctx.response.send_message(embed=embed)
        logger.info(
            f"Created club channel: {formatted_channel_name} and role "
            f"with {len(member_objects)} members by {ctx.user}"
        )

    except Exception as e:
        logger.error(f"Error creating club channel: {e}", exc_info=True)
        await handle_command_error(ctx, e, "クラブチャンネルの作成")


async def add_club_role_member_impl(
    ctx: discord.Interaction,
    members: str,
    role_name: str | None = None,
):
    """クラブロールにメンバーを追加する

    実行可能なロールはCLUB_CATEGORY_NAMEカテゴリのチャンネルに対応するものだけ

    Args:
        ctx: Discord Interaction
        members: 追加するメンバー（メンション形式）
        role_name: 対象のロール名（省略時は実行チャンネル名）
    """
    # 環境変数を一括取得
    config = await EventChannelConfig.load(ctx)
    if not config:
        return

    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return

    # カテゴリーの存在確認
    club_category = await validate_category_exists(ctx, guild, config.club_category_name)
    if not club_category:
        return

    # role_nameが省略された場合は実行チャンネル名を使用
    if role_name is None:
        # コマンド実行チャンネルがCLUB_CATEGORY_NAMEカテゴリーに属しているか確認
        if not isinstance(ctx.channel, discord.TextChannel):
            await send_error_message(ctx, "このコマンドはテキストチャンネルでのみ実行できます。")
            return
        if ctx.channel.category_id != club_category.id:
            await send_error_message(
                ctx,
                f"このコマンドは {config.club_category_name} カテゴリー内でのみ実行できます。",
            )
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

    # 同名のチャンネルがCLUB_CATEGORY_NAMEカテゴリーに存在するか確認
    channel_dict = {ch.name: ch for ch in club_category.text_channels}
    club_channel = channel_dict.get(role_name)
    if not club_channel:
        await send_error_message(
            ctx,
            f"ロール {role.mention} に対応するクラブチャンネルが見つかりません。\n"
            f"このコマンドは{config.club_category_name}カテゴリー内のチャンネルに対応するロールのみ操作可能です。",
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
            title="クラブロールメンバー追加完了",
            description="\n".join(description_parts),
            クラブチャンネル=club_channel.mention,
            ロール=role.name,
            追加人数=len(added_members),
        )

        # Interactionが既に応答済みの場合はfollowupを使用
        if ctx.response.is_done():
            await ctx.followup.send(embed=embed)
        else:
            await ctx.response.send_message(embed=embed)
        logger.info(
            f"Added {len(added_members)} members to club role {role.name} "
            f"(channel: {club_channel.name}) by {ctx.user}"
        )

    except discord.Forbidden:
        await send_error_message(ctx, f"Botに {role.mention} を付与する権限がありません。")
    except Exception as e:
        logger.error(f"Error adding club role members: {e}", exc_info=True)
        await handle_command_error(ctx, e, "クラブロールメンバーの追加")


# ==================== コマンド登録 ====================


def setup(tree: app_commands.CommandTree):
    """クラブチャンネル関連のコマンドを登録する

    デコレーターの順序（重要）:
    1. @command_meta() - メタデータの登録
    2. @tree.command() - コマンドの登録
    3. @require_channel() - チャンネル制限（オプション）
    4. @require_approval() - 承認ミドルウェア（オプション）
    5. @app_commands.describe() - パラメータの説明
    """

    @command_meta(
        category="クラブチャンネル管理",
        icon="🏛️",
        short_description="クラブ用のチャンネルとロールを作成",
        restrictions="• クラブリクエストチャンネルでのみ実行可能",
        examples=[
            "`/create_club_channel channel_name:プログラミング部`",
            "`/create_club_channel channel_name:ロボット研究会 members:@user1 @user2`",
        ],
    )
    @tree.command(
        name="create_club_channel",
        description="新しいクラブチャンネルを作成します",
    )
    @require_channel(channel_name_from_config="clubs_request_channel_name", must_be_in=True)
    @require_approval(description="新しいクラブチャンネルを作成します")
    @app_commands.describe(
        channel_name="作成するクラブチャンネル名",
        members="ロールに追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
    )
    async def create_club_channel(
        ctx: discord.Interaction, channel_name: str, members: str | None = None
    ):
        await create_club_channel_impl(ctx, channel_name, members)

    @command_meta(
        category="ロール管理",
        icon="👥",
        short_description="クラブロールにメンバーを追加",
        restrictions="• 一部ロール以外のみ対象",
        examples=[
            "`/add_club_role_member members:@user1 @user2`",
            "`/add_club_role_member members:@user1 role_name:@1-club`",
        ],
    )
    @tree.command(
        name="add_club_role_member",
        description="クラブチャンネルに紐づくロールにメンバーを追加します",
    )
    @app_commands.describe(
        members="追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
        role_name="対象のロール（@ロール形式で指定。例: @1-club. 省略時は実行チャンネルのロール）",
    )
    async def add_club_role_member(
        ctx: discord.Interaction, members: str, role_name: str | None = None
    ):
        await add_club_role_member_impl(ctx, members, role_name)
