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
from .role_order import role_positions_after_move, target_role_position

logger = getLogger(__name__)

creation_lock = asyncio.Lock()

# サーバーごとの、作成したがまだキャッシュに現れていないロールのID。
# discord.pyはcreate_roleの戻り値をキャッシュに入れず、gatewayのイベントで入れるため、
# その間の上限チェックでロール数を少なく数えないように覚えておく。
pending_role_ids: dict[int, set[int]] = {}


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
    lock: asyncio.Lock = creation_lock,
    pending_role_ids: dict[int, set[int]] = pending_role_ids,
    role_kind: str | None = None,
) -> "Created | Rejected | Failed":
    """上限を確かめてから、チャンネルとそれに紐づくロールを作る

    ロールの作成に失敗したらチャンネルを消して元に戻す。

    Args:
        guild: 作成先のサーバー
        category: 作成先のカテゴリ
        decide_name: チャンネル名を決める（採番など）。使えない場合はRejectedを返す
        role_name_for: 作成されたチャンネルからロール名を決める
        lock: 作成を直列化するLock（テストでは差し替える）
        pending_role_ids: サーバーごとの、作成したがまだキャッシュに現れていないロールのID
            （テストでは差し替える）
        role_kind: ロールの種類（club / event / project）。指定すると、同じ種類のロールの
            並びに合わせて動かす
    """
    pending = pending_role_ids.setdefault(guild.id, set())
    async with lock:
        reason = check_creation_capacity(
            category_channels=len(category.channels),
            guild_channels=len(guild.channels),
            guild_roles=len(guild.roles) + _count_pending_roles(guild, pending),
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

        try:
            role = await guild.create_role(name=role_name_for(channel), mentionable=True)
        except discord.HTTPException as e:
            delete_error = await _rollback_channel(channel)
            return Failed(error=e, leftover_channel=channel if delete_error else None)
        pending.add(role.id)
        if role_kind is not None:
            await _place_role(guild, role, role_kind)
        return Created(channel=channel, role=role)


def _count_pending_roles(guild: discord.Guild, pending: set[int]) -> int:
    """まだキャッシュに現れていないロールの数を返す。現れたものは覚えておくのをやめる"""
    pending.difference_update({role_id for role_id in pending if guild.get_role(role_id)})
    return len(pending)


async def _place_role(guild: discord.Guild, role: discord.Role, kind: str) -> None:
    """作成したロールを、同じ種類のロールの並びに動かす。動かせなくても作成は成功扱いにする

    作成直後のロールはキャッシュになく、他のロールの位置もずれる前のままなので、
    最新のロールの一覧を取得してから位置を決める。
    """
    try:
        roles = await guild.fetch_roles()
        others = [(r.name, r.position) for r in roles if r.id != role.id]
        target = target_role_position(kind, others)
        if target is None:
            return
        positions = role_positions_after_move(
            [(r.id, r.position) for r in roles], role_id=role.id, target=target
        )
        if not positions:
            logger.warning(f"Skipped moving role {role.name}: role positions are inconsistent")
            return
        await guild.edit_role_positions(
            {discord.Object(id=role_id): position for role_id, position in positions.items()}
        )
    except discord.HTTPException as e:
        logger.warning(f"Failed to move role {role.name}: {e}")


async def _rollback_channel(channel: discord.TextChannel) -> discord.HTTPException | None:
    """作成したチャンネルを消す。消せなかった場合はその例外を返す"""
    try:
        await channel.delete()
    except discord.HTTPException as e:
        logger.error(f"Failed to roll back channel {channel.name}: {e}", exc_info=True)
        return e
    return None
