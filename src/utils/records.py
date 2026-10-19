"""チャンネル内の記録の組み立てと送信

記録は対象チャンネルの参加者向けに、そのチャンネルの中に残す。
参加者にした人・加えられた人だけを通知する。
送信の失敗はコマンドを止めず、warningを出すだけにする。
"""

from collections.abc import Sequence
from logging import getLogger
from typing import Protocol

import discord

logger = getLogger(__name__)


class Mentionable(Protocol):
    """メンションできるもの（メンバー、チャンネル、ロール）"""

    @property
    def mention(self) -> str: ...


def _mentions(items: Sequence[Mentionable]) -> str:
    return ", ".join(item.mention for item in items)


def build_creation_embed(
    *,
    kind: str,
    actor: Mentionable,
    channel: Mentionable,
    role: Mentionable,
    members: Sequence[Mentionable],
    failed_members: Sequence[Mentionable],
    join_command: str,
) -> discord.Embed:
    """作成のチャンネル内の記録。あとから来た人のために参加方法を添える"""
    embed = discord.Embed(
        title=f"新しい{kind}",
        description=f"{actor.mention} が {channel.mention} を立てました",
        color=discord.Color.green(),
    )
    embed.add_field(name="ロール", value=role.mention, inline=False)
    if members:
        embed.add_field(name="参加者", value=_mentions(members), inline=False)
    if failed_members:
        embed.add_field(
            name="参加者にできなかった人", value=_mentions(failed_members), inline=False
        )
    embed.add_field(
        name="参加方法",
        value=f"{channel.mention} で `{join_command} members:@自分`",
        inline=False,
    )
    return embed


def build_members_added_embed(
    *, actor: Mentionable, role: Mentionable, members: Sequence[Mentionable]
) -> discord.Embed:
    """メンバー追加のチャンネル内の記録"""
    return discord.Embed(
        title="メンバーが加わりました",
        description=f"{actor.mention} が {_mentions(members)} を {role.mention} に加えました",
        color=discord.Color.green(),
    )


def build_archive_notice_embed(*, actor: Mentionable, restore_command: str) -> discord.Embed:
    """アーカイブのチャンネル内の記録（移動の前に投稿する）"""
    embed = discord.Embed(
        title="このチャンネルをアーカイブします",
        description=f"{actor.mention} がアーカイブします",
        color=discord.Color.light_grey(),
    )
    embed.add_field(name="復元方法", value=f"`{restore_command}`", inline=False)
    return embed


def build_restored_embed(*, actor: Mentionable, channel: Mentionable) -> discord.Embed:
    """復元のチャンネル内の記録（移動の後に投稿する）"""
    return discord.Embed(
        title="復元",
        description=f"{actor.mention} が {channel.mention} を復元しました",
        color=discord.Color.green(),
    )


async def post_channel_record(
    channel: discord.abc.Messageable,
    embed: discord.Embed,
    mention_users: Sequence[discord.abc.User] = (),
    *,
    mention_label: str | None = None,
) -> discord.Message | None:
    """対象チャンネルに記録を送る

    Embed内のメンションは通知されないため、通知したい人は本文でメンションする。
    プッシュ通知には本文だけが出るため、mention_labelで何の通知かを添える
    （例: 「参加者: @a @b」）。

    Returns:
        送信したメッセージ（後で消せるように）。送れなかった場合はNone
    """
    content = " ".join(user.mention for user in mention_users) or None
    if content is not None and mention_label:
        content = f"{mention_label}: {content}"
    allowed_mentions = discord.AllowedMentions(
        everyone=False, users=list(mention_users), roles=False
    )
    try:
        return await channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)
    except discord.HTTPException as e:
        logger.warning(f"Failed to post channel record: {e}")
        return None
