"""投稿をきっかけにした、アーカイブ中のチャンネルの自動復元"""

import asyncio
from collections.abc import Callable, Mapping, Sequence
from logging import getLogger

import discord

from .capacity import CATEGORY_CHANNEL_LIMIT, check_move_capacity
from .channel_order import move_channel
from .channel_utils import resolve_target_text_channel
from .kinds import Kind
from .linking import Located, collect_kind_categories, locate_channel
from .records import build_restored_by_post_embed, post_channel_record

logger = getLogger(__name__)

USER_MESSAGE_TYPES = (discord.MessageType.default, discord.MessageType.reply)


def restore_target(
    message: discord.Message,
    categories: Mapping[Kind, Sequence[discord.CategoryChannel]],
) -> tuple[discord.TextChannel, Kind] | None:
    """投稿が復元のきっかけになるなら、復元するチャンネルと種類を返す

    Args:
        message: 投稿
        categories: 種類ごとの、チャンネルを置くカテゴリ（[通常, アーカイブ]の順）
    """
    if message.author.bot or message.webhook_id is not None:
        return None
    # ピン留めやスレッド作成などのシステムメッセージは、人の投稿として数えない
    if message.type not in USER_MESSAGE_TYPES:
        return None
    # スレッドへの投稿は親チャンネルの動きとして扱う
    if not isinstance(message.channel, (discord.TextChannel, discord.Thread)):
        return None
    channel, _ = resolve_target_text_channel(message.channel)
    if channel is None:
        return None
    located = locate_channel(channel, categories)
    if not isinstance(located, Located) or not located.archived:
        return None
    return channel, located.kind


async def restore_on_post(
    message: discord.Message,
    names_of: Callable[[Kind], tuple[str, str]],
    *,
    locks: dict[int, asyncio.Lock],
) -> None:
    """アーカイブ中のチャンネルに人が投稿したら、その種類のカテゴリへ戻す

    Args:
        message: 投稿
        names_of: 種類の (通常のカテゴリ名, アーカイブカテゴリ名)
        locks: チャンネルごとの、復元を直列化するLock
    """
    guild = message.guild
    if guild is None:
        return
    categories, _ = collect_kind_categories(guild.categories, names_of)
    target = restore_target(message, categories)
    if target is None:
        return
    channel, kind = target
    own, archive = categories[kind][0], categories[kind][-1]
    async with locks.setdefault(channel.id, asyncio.Lock()):
        # 直前の投稿ですでに戻っていることがあるので、最新のカテゴリで確かめ直す
        try:
            fresh = await guild.fetch_channel(channel.id)
        except discord.HTTPException as e:
            logger.warning(f"Failed to fetch {channel.name} before restoring on post: {e}")
            return
        if fresh.category_id != archive.id:
            return
        reason = check_move_capacity(destination_category_channels=len(own.channels))
        if reason is not None:
            logger.warning(f"Could not restore {channel.name} on post: {reason}")
            await _reply_quietly(
                message,
                f"`{own.name}` カテゴリーがチャンネル数の上限（{CATEGORY_CHANNEL_LIMIT}）に"
                "達しているため、このチャンネルを戻せませんでした。サーバー管理者に連絡してください。",
            )
            return
        try:
            await move_channel(channel, own, kind)
        except discord.HTTPException as e:
            logger.warning(f"Failed to restore {channel.name} on post: {e}")
            return
    logger.info(f"Restored {kind.key} channel {channel.name} on post by {message.author}")
    await post_channel_record(
        channel, build_restored_by_post_embed(author=message.author, restored_to=own.name)
    )


async def _reply_quietly(message: discord.Message, text: str) -> None:
    """投稿に返信する。投稿者への通知はしない。送れなくても例外は出さない"""
    try:
        await message.reply(text, mention_author=False)
    except discord.HTTPException as e:
        logger.warning(f"Failed to reply to {message.id}: {e}")
