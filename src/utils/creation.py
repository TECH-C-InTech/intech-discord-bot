"""チャンネルとロールの作成の共通処理

上限チェックから作成までをサーバー全体で1つのLockの中で行い、
並行した作成が上限や採番をすり抜けないようにする（botは1プロセスで動く前提）。
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from logging import getLogger

import discord

from .capacity import check_creation_capacity

logger = getLogger(__name__)

creation_lock = asyncio.Lock()
ROLE_CACHE_POLL_INTERVAL = 0.05


@dataclass(frozen=True)
class Created:
    channel: discord.TextChannel
    role: discord.Role


@dataclass(frozen=True)
class Rejected:
    reason: str


@dataclass(frozen=True)
class Failed:
    """Discordの操作に失敗した。ロールバックできなかったチャンネルがあればleftover_channelに入る"""

    error: Exception
    leftover_channel: discord.TextChannel | None


async def create_channel_with_role(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    *,
    decide_name: Callable[[discord.Guild, discord.CategoryChannel], "str | Rejected"],
    role_name_for: Callable[[discord.TextChannel], str],
    validate_created_name: Callable[
        [discord.Guild, discord.TextChannel], str | None
    ] = lambda guild, channel: None,
    lock: asyncio.Lock = creation_lock,
    role_cache_timeout: float = 5.0,
) -> "Created | Rejected | Failed":
    """上限を確かめてから、チャンネルとそれに紐づくロールを作る

    ロールの作成に失敗したらチャンネルを消して元に戻す。

    Args:
        guild: 作成先のサーバー
        category: 作成先のカテゴリ
        decide_name: チャンネル名を決める（採番など）。使えない場合はRejectedを返す
        role_name_for: 作成されたチャンネルからロール名を決める
        validate_created_name: Discordが正規化した実際のチャンネル名を検証する。
            使えない場合は理由を返す
        lock: 作成を直列化するLock（テストでは差し替える）
        role_cache_timeout: 作成したロールがキャッシュに現れるのを待つ秒数。
            次の作成の上限チェックでロール数を正しく数えるために待つ
    """
    async with lock:
        reason = check_creation_capacity(
            category_channels=len(category.channels),
            guild_channels=len(guild.channels),
            guild_roles=len(guild.roles),
        )
        if reason is not None:
            return Rejected(reason)

        name = decide_name(guild, category)
        if isinstance(name, Rejected):
            return name

        try:
            channel = await guild.create_text_channel(name=name, category=category)
        except discord.HTTPException as e:
            return Failed(error=e, leftover_channel=None)

        created_name_reason = validate_created_name(guild, channel)
        if created_name_reason is not None:
            delete_error = await _rollback_channel(channel)
            if delete_error is not None:
                return Failed(error=delete_error, leftover_channel=channel)
            return Rejected(created_name_reason)

        try:
            role = await guild.create_role(name=role_name_for(channel), mentionable=True)
        except discord.HTTPException as e:
            delete_error = await _rollback_channel(channel)
            return Failed(error=e, leftover_channel=channel if delete_error else None)
        await _wait_for_role_cache(guild, role, timeout=role_cache_timeout)
        return Created(channel=channel, role=role)


async def _rollback_channel(channel: discord.TextChannel) -> discord.HTTPException | None:
    """作成したチャンネルを消す。消せなかった場合はその例外を返す"""
    try:
        await channel.delete()
    except discord.HTTPException as e:
        logger.error(f"Failed to roll back channel {channel.name}: {e}", exc_info=True)
        return e
    return None


async def _wait_for_role_cache(guild: discord.Guild, role: discord.Role, *, timeout: float) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while guild.get_role(role.id) is None:
        if loop.time() >= deadline:
            logger.warning(f"Role {role.id} did not appear in cache within {timeout}s")
            return
        await asyncio.sleep(ROLE_CACHE_POLL_INTERVAL)
