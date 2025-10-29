"""チャンネル関連のユーティリティ"""

import re
from logging import getLogger
from typing import Optional

import discord

logger = getLogger(__name__)


def get_next_event_index(
    guild: discord.Guild, event_category_name: str, archive_event_category_name: str
) -> int:
    """
    eventカテゴリーとarchivedカテゴリーのチャンネルから、
    最大のインデックス番号を見つけて+1した値を返す

    チャンネル名のパターン: {index}-{name}
    例: 1-新歓イベント, 2-ハッカソン

    Args:
        guild: Discordサーバー
        event_category_name: イベントカテゴリー名
        archive_event_category_name: アーカイブカテゴリー名

    Returns:
        次のインデックス番号
    """
    max_index = 0

    # eventカテゴリーのチャンネルをチェック
    event_category = discord.utils.get(guild.categories, name=event_category_name)
    if event_category:
        for channel in event_category.channels:
            match = re.match(r"^(\d+)-", channel.name)
            if match:
                index = int(match.group(1))
                max_index = max(max_index, index)

    # archivedカテゴリーのチャンネルをチェック
    archive_category = discord.utils.get(
        guild.categories, name=archive_event_category_name
    )
    if archive_category:
        for channel in archive_category.channels:
            match = re.match(r"^(\d+)-", channel.name)
            if match:
                index = int(match.group(1))
                max_index = max(max_index, index)

    return max_index + 1


async def validate_category_exists(
    ctx: discord.Interaction, guild: discord.Guild, category_name: str
) -> Optional[discord.CategoryChannel]:
    """
    カテゴリーが存在するか確認し、存在しない場合はエラーメッセージを返す

    Args:
        ctx: Discord Interaction
        guild: Discord Guild
        category_name: カテゴリー名

    Returns:
        カテゴリーチャンネル。存在しない場合はNoneを返し、エラーメッセージを送信する
    """
    category_channel = discord.utils.get(guild.categories, name=category_name)
    if not category_channel:
        logger.warning(f"Category '{category_name}' not found in guild '{guild.name}'")
        logger.warning(f"Please update the environment variable. now: {category_name}")
        await ctx.response.send_message(
            f"❌ カテゴリー '{category_name}' が存在しません。サーバー設定を更新する必要があるため、管理者に連絡してください。",
            ephemeral=True,
        )
    return category_channel
