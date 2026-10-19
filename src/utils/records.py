"""記録（ログチャンネルとチャンネル内の記録）の組み立てと送信

記録は読み手ごとに残す。ログチャンネルはサーバー全体向けで誰も通知しない。
チャンネル内の記録は対象チャンネルの参加者向けで、誘われた人・加えられた人だけを通知する。
送信の失敗はコマンドを止めず、warningを出すだけにする。
"""

from collections.abc import Sequence
from logging import getLogger
from typing import Protocol

import discord

logger = getLogger(__name__)

REQUIRED_LOG_PERMISSIONS = ("view_channel", "send_messages", "embed_links")


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
) -> discord.Embed:
    """作成の記録（ログチャンネルとチャンネル内の記録で共通）"""
    embed = discord.Embed(
        title=f"{kind}が作成されました",
        description=f"{channel.mention} と {role.mention}",
        color=discord.Color.green(),
    )
    embed.add_field(name="作成した人", value=actor.mention, inline=False)
    if members:
        embed.add_field(name="誘われた人", value=_mentions(members), inline=False)
    if failed_members:
        embed.add_field(
            name="ロールを付与できなかった人", value=_mentions(failed_members), inline=False
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
    return discord.Embed(
        title="このチャンネルをアーカイブします",
        description=f"{actor.mention} の操作です。`{restore_command}` で戻せます。",
        color=discord.Color.light_grey(),
    )


def build_archived_log_embed(*, actor: Mentionable, channel: Mentionable) -> discord.Embed:
    """アーカイブのログ（移動の成功後に送る）"""
    return discord.Embed(
        title="チャンネルがアーカイブされました",
        description=f"{channel.mention}（{actor.mention} がアーカイブ）",
        color=discord.Color.light_grey(),
    )


def build_restored_embed(*, actor: Mentionable, channel: Mentionable) -> discord.Embed:
    """復元の記録（ログチャンネルとチャンネル内の記録で共通）"""
    return discord.Embed(
        title="チャンネルが復元されました",
        description=f"{channel.mention}（{actor.mention} が復元）",
        color=discord.Color.green(),
    )


async def post_log(guild: discord.Guild, log_channel_name: str, embed: discord.Embed) -> None:
    """ログチャンネルに記録を送る。誰も通知しない"""
    log_channel = discord.utils.get(guild.text_channels, name=log_channel_name)
    if log_channel is None:
        logger.warning(f"Log channel '{log_channel_name}' not found in guild {guild.name}")
        return
    try:
        await log_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException as e:
        logger.warning(f"Failed to post log to '{log_channel_name}': {e}")


async def post_channel_record(
    channel: discord.abc.Messageable,
    embed: discord.Embed,
    mention_users: Sequence[discord.abc.User] = (),
) -> discord.Message | None:
    """対象チャンネルに記録を送る

    Embed内のメンションは通知されないため、通知したい人は本文でメンションする。

    Returns:
        送信したメッセージ（後で消せるように）。送れなかった場合はNone
    """
    content = " ".join(user.mention for user in mention_users) or None
    allowed_mentions = discord.AllowedMentions(
        everyone=False, users=list(mention_users), roles=False
    )
    try:
        return await channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)
    except discord.HTTPException as e:
        logger.warning(f"Failed to post channel record: {e}")
        return None


def find_log_channel_problems(guild: discord.Guild, log_channel_name: str) -> list[str]:
    """ログチャンネルが無い、またはbotが送れない場合にその内容を返す"""
    log_channel = discord.utils.get(guild.text_channels, name=log_channel_name)
    if log_channel is None:
        return [f"ログチャンネル '{log_channel_name}' がサーバー {guild.name} にありません"]
    permissions = log_channel.permissions_for(guild.me)
    missing = [name for name in REQUIRED_LOG_PERMISSIONS if not getattr(permissions, name)]
    if missing:
        return [
            f"botにログチャンネル '{log_channel_name}' の権限がありません: {', '.join(missing)}"
        ]
    return []
