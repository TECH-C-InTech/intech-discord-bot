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
    validate_channel_in_category,
    validate_channel_restriction,
)

logger = getLogger(__name__)


async def create_event_channel(
    ctx: discord.Interaction,
    channel_name: str,
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

    try:
        # 次のインデックス番号を取得
        next_index = get_next_event_index(
            guild, config.event_category_name, config.archive_event_category_name
        )

        # チャンネル名を {index}-{name} の形式で構築
        formatted_channel_name = f"{next_index}-{channel_name}"

        channel = await guild.create_text_channel(
            name=formatted_channel_name, category=category_channel
        )

        # 成功メッセージ
        embed = create_success_embed(
            title="イベントチャンネル作成完了",
            description=f"{channel.mention} を作成しました",
            チャンネル名=formatted_channel_name,
            インデックス=next_index,
        )

        await ctx.response.send_message(embed=embed)
        logger.info(
            f"Created channel: {formatted_channel_name} (index: {next_index}) by {ctx.user}"
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

    # コマンド実行チャンネルの確認
    if not await validate_channel_restriction(
        ctx, config.event_request_channel_name, must_be_in=False
    ):
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
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel:
            await send_error_message(
                ctx, f"チャンネル '{channel_name}' が見つかりません。"
            )
            return
    else:
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
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel:
            await send_error_message(
                ctx, f"チャンネル '{channel_name}' が見つかりません。"
            )
            return
    else:
        channel = ctx.channel

    # チャンネルがアーカイブカテゴリーに属しているか確認
    if not await validate_channel_in_category(
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


def setup(tree: app_commands.CommandTree):
    """イベントチャンネル関連のコマンドを登録する"""

    @tree.command(
        name="create_event_channel", description="新しいイベントチャンネルを作成します"
    )
    @app_commands.describe(channel_name="作成するイベントチャンネル名")
    async def create_event_channel_cmd(ctx: discord.Interaction, channel_name: str):
        await create_event_channel(ctx, channel_name)

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
