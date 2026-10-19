"""チャンネル関連のユーティリティ

ドキュメント ADD_COMMAND.md に従って実装
より詳細なドキュメントとエラーハンドリングを追加
"""

from logging import getLogger
import re
from typing import TYPE_CHECKING, Optional

import discord

from .message_utils import send_error_message

if TYPE_CHECKING:
    from discord.interactions import InteractionChannel

logger = getLogger(__name__)


def get_next_event_index(
    guild: discord.Guild,
    event_category_name: str,
    archive_event_category_name: str,
) -> int:
    """イベントカテゴリーとアーカイブカテゴリーから次のインデックス番号を取得する

    チャンネル名のパターン: e{index}-{name}
    例: e001-新歓イベント, e002-ハッカソン

    両方のカテゴリーのチャンネルから最大のインデックス番号を見つけて+1した値を返す。
    これにより、アーカイブされたチャンネルも考慮した連番を維持できる。

    Args:
        guild: Discordサーバー
        event_category_name: イベントカテゴリー名
        archive_event_category_name: アーカイブカテゴリー名

    Returns:
        次のインデックス番号（最小値は1）
    """
    max_index = 0
    pattern = re.compile(r"^e(\d{3})-")

    # イベントカテゴリーのチャンネルをチェック
    event_category = discord.utils.get(guild.categories, name=event_category_name)
    if event_category:
        for channel in event_category.channels:
            match = pattern.match(channel.name)
            if match:
                index = int(match.group(1))
                max_index = max(max_index, index)
                logger.debug(f"Found event channel: {channel.name} with index {index}")

    # アーカイブカテゴリーのチャンネルをチェック
    archive_category = discord.utils.get(guild.categories, name=archive_event_category_name)
    if archive_category:
        for channel in archive_category.channels:
            match = pattern.match(channel.name)
            if match:
                index = int(match.group(1))
                max_index = max(max_index, index)
                logger.debug(f"Found archived channel: {channel.name} with index {index}")

    next_index = max_index + 1
    logger.info(f"Next event index: {next_index} (max found: {max_index}) in guild '{guild.name}'")
    return next_index


def get_next_project_index(
    guild: discord.Guild,
    project_category_name: str,
    archive_project_category_name: str,
) -> int:
    """プロジェクトカテゴリーとアーカイブカテゴリーから次のインデックス番号を取得する

    チャンネル名のパターン: p{index}-{name}
    例: p001-新規プロジェクト, p002-研究開発

    両方のカテゴリーのチャンネルから最大のインデックス番号を見つけて+1した値を返す。
    これにより、アーカイブされたチャンネルも考慮した連番を維持できる。

    Args:
        guild: Discordサーバー
        project_category_name: プロジェクトカテゴリー名
        archive_project_category_name: アーカイブカテゴリー名

    Returns:
        次のインデックス番号（最小値は1）
    """
    max_index = 0
    pattern = re.compile(r"^p(\d{3})-")

    # プロジェクトカテゴリーのチャンネルをチェック
    project_category = discord.utils.get(guild.categories, name=project_category_name)
    if project_category:
        for channel in project_category.channels:
            match = pattern.match(channel.name)
            if match:
                index = int(match.group(1))
                max_index = max(max_index, index)
                logger.debug(f"Found project channel: {channel.name} with index {index}")

    # アーカイブカテゴリーのチャンネルをチェック
    archive_category = discord.utils.get(guild.categories, name=archive_project_category_name)
    if archive_category:
        for channel in archive_category.channels:
            match = pattern.match(channel.name)
            if match:
                index = int(match.group(1))
                max_index = max(max_index, index)
                logger.debug(f"Found archived project channel: {channel.name} with index {index}")

    next_index = max_index + 1
    logger.info(
        f"Next project index: {next_index} (max found: {max_index}) in guild '{guild.name}'"
    )
    return next_index


async def validate_category_exists(
    ctx: discord.Interaction, guild: discord.Guild, category_name: str
) -> Optional[discord.CategoryChannel]:
    """カテゴリーが存在するか確認する

    カテゴリーが存在しない場合はユーザーにエラーメッセージを表示し、
    管理者向けのログも出力する。

    Args:
        ctx: Discord Interaction
        guild: Discord Guild
        category_name: カテゴリー名

    Returns:
        カテゴリーチャンネル。存在しない場合はNoneを返し、エラーメッセージを送信する
    """
    category_channel = discord.utils.get(guild.categories, name=category_name)

    if not category_channel:
        logger.warning(
            f"Category '{category_name}' not found in guild '{guild.name}'"
            f" (requested by {ctx.user})"
        )
        logger.warning(f"Available categories: {[cat.name for cat in guild.categories]}")
        await send_error_message(
            ctx,
            f"カテゴリー `{category_name}` が存在しません。\n"
            f"サーバー設定を更新する必要があるため、管理者に連絡してください。",
        )
        return None

    logger.debug(f"Category '{category_name}' found with ID: {category_channel.id}")
    return category_channel


async def get_channel_by_name(
    ctx: discord.Interaction,
    guild: discord.Guild,
    channel_name: str,
) -> Optional[discord.TextChannel]:
    """チャンネル名からチャンネルを検索する

    Args:
        ctx: Discord Interaction
        guild: Discordギルド
        channel_name: チャンネル名

    Returns:
        チャンネルオブジェクト。見つからない場合はNone
    """
    channel = discord.utils.get(guild.text_channels, name=channel_name)

    if not channel:
        await send_error_message(
            ctx,
            f"チャンネル `{channel_name}` が見つかりません。\nチャンネル名を確認してください。",
        )
        logger.warning(
            f"Channel '{channel_name}' not found in guild '{guild.name}' (requested by {ctx.user})"
        )
        return None

    logger.debug(f"Channel '{channel_name}' found with ID: {channel.id}")
    return channel


def resolve_target_text_channel(
    channel: "InteractionChannel | None",
) -> tuple[discord.TextChannel | None, bool]:
    """コマンドの対象にするテキストチャンネルを、実行された場所から決める

    スレッドから実行された場合は親のテキストチャンネルを対象にする。

    Args:
        channel: コマンドが実行された場所（Interaction.channel）

    Returns:
        (対象のテキストチャンネル, スレッドの親を対象にしたか)。
        対象にできない場所（フォーラムのスレッド、ボイスチャンネル等）では (None, False)
    """
    if isinstance(channel, discord.TextChannel):
        return channel, False
    if isinstance(channel, discord.Thread) and isinstance(channel.parent, discord.TextChannel):
        return channel.parent, True
    return None, False


async def resolve_target_text_channel_or_error(
    ctx: discord.Interaction,
) -> tuple[discord.TextChannel | None, bool]:
    """実行された場所から対象のテキストチャンネルを決め、決められなければ本人にエラーを返す"""
    channel, via_thread = resolve_target_text_channel(ctx.channel)
    if channel is None:
        await send_error_message(
            ctx, "このコマンドはテキストチャンネルかそのスレッドでのみ実行できます。"
        )
    return channel, via_thread


def thread_target_note(channel: discord.TextChannel, via_thread: bool) -> str:
    """スレッドの親チャンネルを対象にした場合に、本人への返信に添える一文"""
    if not via_thread:
        return ""
    return f"\n（スレッドから実行したため、親チャンネル {channel.mention} を対象にしました）"
