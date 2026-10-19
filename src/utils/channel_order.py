"""カテゴリ内のチャンネルを番号順に並べる

チャンネルの位置（position）はサーバー全体で通しの値で、カテゴリ内ではその小さい順に
表示される。カテゴリを変えて移動したチャンネルは移動前の位置を持ち越すため、
移動先で不自然な場所に入る。最新の位置をもとに、カテゴリ内を番号順に並べ直す。
"""

from logging import getLogger
from typing import TYPE_CHECKING

import discord

from .kinds import Kind
from .numbering import number_of

if TYPE_CHECKING:
    from discord.types.guild import ChannelPositionUpdate

logger = getLogger(__name__)


def sorted_channel_positions(prefix: str, channels: list[tuple[int, str, int]]) -> dict[int, int]:
    """カテゴリ内のチャンネルを番号の小さい順に並べたときの、変わる位置だけを返す

    Args:
        prefix: 並べる番号の種類（e / p / c）
        channels: カテゴリ内のテキストチャンネルの (ID, 名前, 最新の位置)

    Returns:
        チャンネルIDと新しい位置。番号のないチャンネルは今の並びのまま上に置く
    """
    if not channels:
        return {}
    # 今の表示順（位置が同じならIDの小さい順）
    current = sorted(channels, key=lambda c: (c[2], c[0]))
    # 安定ソートなので、番号のないチャンネル（0扱い）は今の並びのまま先頭に残る
    desired = sorted(current, key=lambda c: number_of(prefix, c[1]) or 0)
    base = current[0][2]
    positions = {cid: position for cid, _, position in channels}
    return {
        cid: base + index
        for index, (cid, _, _) in enumerate(desired)
        if positions[cid] != base + index
    }


async def sort_category(guild: discord.Guild, *, category_id: int, prefix: str) -> None:
    """カテゴリ内のテキストチャンネルを番号順に並べ直す。失敗しても例外は出さない

    キャッシュの位置は古いことがあるため、最新の一覧を取得してから並べる。
    discord.pyにはチャンネルの位置をまとめて変える公開メソッドがないため、
    Channel.edit(position=...)が内部で使っているAPIを直接呼ぶ。
    """
    try:
        channels = await guild.fetch_channels()
        targets = [
            (c.id, c.name, c.position)
            for c in channels
            if isinstance(c, discord.TextChannel) and c.category_id == category_id
        ]
        positions = sorted_channel_positions(prefix, targets)
        if not positions:
            return
        payload: "list[ChannelPositionUpdate]" = [
            {"id": cid, "position": position} for cid, position in positions.items()
        ]
        await guild._state.http.bulk_channel_update(guild.id, payload)
    except Exception as e:
        # 並べ直しは移動のおまけなので、何が起きても移動は成功扱いにする
        logger.warning(f"Failed to sort channels in category {category_id}: {e}", exc_info=True)


async def move_channel(
    channel: discord.TextChannel, destination: discord.CategoryChannel, kind: Kind
) -> None:
    """チャンネルをカテゴリへ移し、移動先をその種類の番号順に並べ直す

    移動に失敗したら例外を出す。並べ直しの失敗は移動の成否に影響しない。
    """
    await channel.edit(category=destination, sync_permissions=True)
    await sort_category(channel.guild, category_id=destination.id, prefix=kind.prefix)
