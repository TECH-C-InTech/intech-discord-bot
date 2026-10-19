"""記録（ログチャンネルとチャンネル内の記録）の組み立てと送信

記録は読み手ごとに残す。ログチャンネルはサーバー全体向けで誰も通知しない。
チャンネル内の記録は対象チャンネルの参加者向けで、参加者にした人・加えられた人だけを通知する。
送信の失敗はコマンドを止めず、warningを出すだけにする。
"""

from collections.abc import Sequence
from logging import getLogger
from typing import Protocol

import discord

from .channel_name import normalize_channel_name

logger = getLogger(__name__)

REQUIRED_LOG_PERMISSIONS = ("view_channel", "send_messages", "embed_links")


class Mentionable(Protocol):
    """メンションできるもの（メンバー、チャンネル、ロール）"""

    @property
    def mention(self) -> str: ...


class NamedChannel(Mentionable, Protocol):
    """メンションでき、名前を持つチャンネル"""

    @property
    def name(self) -> str: ...


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
    """作成の記録（ログチャンネルとチャンネル内の記録で共通）

    ログチャンネルは新しい活動の掲示板も兼ねるため、参加方法を添える。
    """
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


def build_archived_log_embed(
    *, actor: Mentionable, channel: NamedChannel, restore_command: str
) -> discord.Embed:
    """アーカイブのログ（移動の成功後に送る）

    ログチャンネルから復元するにはチャンネルの指定が要るため、復元方法に名前まで書く。
    """
    embed = discord.Embed(
        title="アーカイブ",
        description=f"{actor.mention} が {channel.mention} をアーカイブしました",
        color=discord.Color.light_grey(),
    )
    embed.add_field(
        name="復元方法",
        value=f"`{restore_command} channel_name:{channel.name}`",
        inline=False,
    )
    return embed


def build_restored_embed(*, actor: Mentionable, channel: Mentionable) -> discord.Embed:
    """復元の記録（ログチャンネルとチャンネル内の記録で共通）"""
    return discord.Embed(
        title="復元",
        description=f"{actor.mention} が {channel.mention} を復元しました",
        color=discord.Color.green(),
    )


def _find_log_channel(guild: discord.Guild, log_channel_name: str) -> discord.TextChannel | None:
    # 設定値の大文字・空白はDiscordが正規化した実際の名前とずれうるため、正規化して探す
    return discord.utils.get(guild.text_channels, name=normalize_channel_name(log_channel_name))


async def post_log(guild: discord.Guild, log_channel_name: str, embed: discord.Embed) -> None:
    """ログチャンネルに記録を送る。誰も通知しない"""
    log_channel = _find_log_channel(guild, log_channel_name)
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
    log_channel = _find_log_channel(guild, log_channel_name)
    if log_channel is None:
        return [f"ログチャンネル '{log_channel_name}' がサーバー {guild.name} にありません"]
    permissions = log_channel.permissions_for(guild.me)
    missing = [name for name in REQUIRED_LOG_PERMISSIONS if not getattr(permissions, name)]
    if missing:
        return [
            f"botにログチャンネル '{log_channel_name}' の権限がありません: {', '.join(missing)}"
        ]
    return []
