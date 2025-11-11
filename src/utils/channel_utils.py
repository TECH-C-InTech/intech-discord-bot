"""チャンネル関連のユーティリティ

ドキュメント ADD_COMMAND.md に従って実装
より詳細なドキュメントとエラーハンドリングを追加
"""

import asyncio
from logging import getLogger
import re
from typing import Optional

import discord

from .message_utils import send_error_message

logger = getLogger(__name__)


def get_next_event_index(
    guild: discord.Guild,
    event_category_name: str,
    archive_event_category_name: str,
) -> int:
    """イベントカテゴリーとアーカイブカテゴリーから次のインデックス番号を取得する

    チャンネル名のパターン: {index}-{name}
    例: 1-新歓イベント, 2-ハッカソン

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
    pattern = re.compile(r"^(\d+)-")

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

async def sort_channels_by_index(category: discord.CategoryChannel, target_channel: discord.TextChannel | None = None) -> None:
    """カテゴリー内のチャンネルを正しい位置に配置する

    target_channel が指定されている場合、そのチャンネルをインデックス番号に基づいた
    正しい位置に一度だけ移動します。指定されていない場合は処理を行いません。

    カテゴリー移動直後（position=0 に固定されている状態）での使用を想定しています。

    Args:
        category: 対象のカテゴリーチャンネル
        target_channel: 配置するチャンネル（省略時は処理なし）
    Note:
        - インデックス付きチャンネル（^(\\d+)-）のみが対象
        - target_channel のインデックスに基づいて正しい位置を計算
        - 1度の API 呼び出しでチャンネルを配置
    """
    if target_channel is None:
        return

    pattern = re.compile(r"^(\d+)-")
    match = pattern.match(target_channel.name)
    if not match:
        logger.warning(
            f"Channel '{target_channel.name}' does not have an index prefix"
        )
        return

    target_index = int(match.group(1))
    target_position = target_index - 1

    try:
        if target_channel.position != target_position:
            await target_channel.edit(position=target_position)
            logger.info(
                f"Positioned channel '{target_channel.name}' (index={target_index}) "
                f"to position {target_channel.position} in category '{category.name}'"
            )
        else:
            logger.info(
                f"Channel '{target_channel.name}' already at correct position {target_position}"
            )
    except discord.Forbidden:
        logger.error(
            f"Permission denied: Cannot edit position for channel '{target_channel.name}'"
        )
    except discord.HTTPException as e:
        logger.error(f"HTTP error while positioning channel '{target_channel.name}': {e}")


async def reset_all_event_positions_in_category(
    category: discord.CategoryChannel,
) -> int:
    """カテゴリー内のすべてのインデックス付きチャンネルをリセット

    チャンネル名が {index}-{name} 形式の場合、
    position = index となるように逐次リセットします。

    Args:
        category: 対象のカテゴリーチャンネル

    Returns:
        リセットしたチャンネル数

    Note:
        - インデックス付きチャンネル（^(\\d+)-）のみが対象
        - 各 channel.edit() 間に 0.05 秒のスリープを挿入（API制限回避）
        - 既に正しい position のチャンネルはスキップ
    """
    pattern = re.compile(r"^(\d+)-")

    # インデックス付きチャンネルを抽出
    channels_with_index = []
    for channel in category.text_channels:
        match = pattern.match(channel.name)
        if match:
            index = int(match.group(1))
            channels_with_index.append((index, channel))

    if not channels_with_index:
        logger.debug(f"No indexed channels found in category '{category.name}'")
        return 0

    # インデックスでソート
    channels_with_index.sort(key=lambda x: x[0])

    # position = index で逐次リセット
    reset_count = 0
    for index, channel in channels_with_index:
        target_position = index - 1
        # 既に正しい位置の場合はスキップ
        if channel.position == target_position:
            logger.debug(
                f"Channel '{channel.name}' already at correct position {target_position}"
            )
        else:
            try:
                await channel.edit(position=target_position)
                reset_count += 1
                logger.info(
                    f"Reset channel '{channel.name}' (index={index}) to position {target_position}"
                )
            except discord.Forbidden:
                logger.error(
                    f"Permission denied: Cannot edit position for channel '{channel.name}'"
                )
            except discord.HTTPException as e:
                logger.error(
                    f"HTTP error while resetting position for channel '{channel.name}': {e}"
                )

        await asyncio.sleep(2)

    # 全チャンネルのpositionを表示
    for channel in category.text_channels:
        logger.info(
            f"Channel '{channel.name}' final position: {channel.position}"
        )

    logger.info(
        f"Reset {reset_count} channels in category '{category.name}'"
    )
    return reset_count
