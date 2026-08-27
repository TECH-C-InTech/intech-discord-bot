"""チャンネル関連のユーティリティ

ドキュメント ADD_COMMAND.md に従って実装
より詳細なドキュメントとエラーハンドリングを追加
"""

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


def find_highest_numbered_role(guild: discord.Guild) -> Optional[discord.Role]:
    """番号のみのロール（イベントロール）の中で最も上位のものを見つける

    イベントロールは番号のみ（例: "1", "2", "3"）で作成されているため、
    全てのロールから番号のみのロールを検出し、その中で最も上位（position が最大）のロールを返す。

    Args:
        guild: Discordサーバー

    Returns:
        番号のみのロールの中で最も上位のロール。見つからない場合はNone
    """
    numbered_roles = []

    for role in guild.roles:
        # ロール名が数字のみかチェック
        if role.name.isdigit():
            numbered_roles.append(role)
            logger.debug(f"Found numbered role: {role.name} (position: {role.position})")

    if not numbered_roles:
        logger.debug("No numbered roles found in guild")
        return None

    # positionが最も大きいもの（最も上位）を返す
    highest_role = max(numbered_roles, key=lambda r: r.position)
    logger.info(
        f"Highest numbered role: {highest_role.name} "
        f"(position: {highest_role.position}) in guild '{guild.name}'"
    )
    return highest_role


async def position_role_above_numbered_roles(
    role: discord.Role,
    guild: discord.Guild,
) -> None:
    """ロールを番号のみのロール（イベントロール）より上に配置する

    番号のみのロール（イベントロール）を検出し、その中で最も上位のロールの
    1つ上にロールを移動する。番号のみのロールが存在しない場合は何もしない。

    Args:
        role: 配置するロール
        guild: Discordサーバー
    """
    highest_numbered_role = find_highest_numbered_role(guild)

    if highest_numbered_role is None:
        logger.info(f"No numbered roles found, skipping position adjustment for role '{role.name}'")
        return

    # 番号のみのロールの1つ上に配置
    target_position = highest_numbered_role.position + 1

    try:
        await role.edit(position=target_position)
        logger.info(
            f"Successfully positioned role '{role.name}' at position {target_position} "
            f"(above numbered role '{highest_numbered_role.name}')"
        )
    except discord.Forbidden:
        logger.error(f"Permission denied to move role '{role.name}' to position {target_position}")
        raise
    except discord.HTTPException as e:
        logger.error(f"Failed to move role '{role.name}': {e}")
        raise
