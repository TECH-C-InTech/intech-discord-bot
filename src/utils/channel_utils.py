"""チャンネル関連のユーティリティ

ドキュメント ADD_COMMAND.md に従って実装
より詳細なドキュメントとエラーハンドリングを追加
"""

from logging import getLogger
from typing import TYPE_CHECKING, Optional

import discord

from .kinds import Kind
from .message_utils import send_error_message
from .numbering import next_number

if TYPE_CHECKING:
    from discord.interactions import InteractionChannel

logger = getLogger(__name__)


def _channel_names_in(guild: discord.Guild, *category_names: str) -> list[str]:
    names: list[str] = []
    for category_name in category_names:
        category = discord.utils.get(guild.categories, name=category_name)
        if category:
            names.extend(channel.name for channel in category.channels)
    return names


def get_next_number(
    guild: discord.Guild, kind: Kind, category_names: tuple[str, ...]
) -> int | None:
    """種類の次の番号を返す。999まで使い切っていたらNone

    種類のカテゴリ（通常とアーカイブ）にあるチャンネル名に加え、ロール名の番号も避ける。
    チャンネルだけ消されてロールが残っている番号を再利用しないため。
    """
    return next_number(
        kind.prefix,
        [*_channel_names_in(guild, *category_names), *(role.name for role in guild.roles)],
    )


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
    return f"\n（スレッドから実行したため、親チャンネル {channel.mention} に対して行いました）"
