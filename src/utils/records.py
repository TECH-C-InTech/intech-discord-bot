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

EMBED_FIELD_VALUE_LIMIT = 1024
MESSAGE_CONTENT_LIMIT = 2000


class Mentionable(Protocol):
    """メンションできるもの（メンバー、チャンネル、ロール）"""

    @property
    def mention(self) -> str: ...


def _mentions(items: Sequence[Mentionable]) -> str:
    return ", ".join(item.mention for item in items)


def _add_mention_fields(embed: discord.Embed, name: str, items: Sequence[Mentionable]) -> None:
    """メンションの一覧を、Embedの項目の上限（1024文字）に収まるよう分けて足す"""
    chunks: list[list[str]] = []
    length = 0
    for item in items:
        mention = item.mention
        if chunks and length + len(", ") + len(mention) <= EMBED_FIELD_VALUE_LIMIT:
            chunks[-1].append(mention)
            length += len(", ") + len(mention)
        else:
            chunks.append([mention])
            length = len(mention)
    for index, chunk in enumerate(chunks, start=1):
        label = name if index == 1 else f"{name}（{index}）"
        embed.add_field(name=label, value=", ".join(chunk), inline=False)


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
        title=f"{kind}作成",
        description=f"{actor.mention} が {channel.mention} を立てました",
        color=discord.Color.green(),
    )
    embed.add_field(name="ロール", value=role.mention, inline=False)
    _add_mention_fields(embed, "参加者", members)
    _add_mention_fields(embed, "参加者にできなかった人", failed_members)
    embed.add_field(
        name="参加方法",
        value=f"{channel.mention} で `{join_command}` を実行し、`members` に自分をメンションする",
        inline=False,
    )
    return embed


def build_members_added_embed(
    *, actor: Mentionable, role: Mentionable, members: Sequence[Mentionable]
) -> discord.Embed:
    """参加者の追加のチャンネル内の記録"""
    return discord.Embed(
        title="参加者の追加",
        description=f"{actor.mention} が {_mentions(members)} を {role.mention} に加えました",
        color=discord.Color.green(),
    )


def build_members_removed_embed(
    *, actor: Mentionable, role: Mentionable, members: Sequence[Mentionable]
) -> discord.Embed:
    """参加者の削除のチャンネル内の記録（外された人は通知しないので、Embedの中にだけ書く）"""
    return discord.Embed(
        title="参加者の削除",
        description=f"{actor.mention} が {_mentions(members)} を {role.mention} から外しました",
        color=discord.Color.light_grey(),
    )


def build_archive_notice_embed(*, actor: Mentionable, restore_command: str) -> discord.Embed:
    """アーカイブのチャンネル内の記録（移動の前に投稿する）"""
    embed = discord.Embed(
        title="アーカイブ",
        description=f"{actor.mention} がこのチャンネルをアーカイブしました",
        color=discord.Color.light_grey(),
    )
    embed.add_field(
        name="復元方法",
        value=f"このチャンネルに投稿すると自動で戻ります（手動なら`{restore_command}`）",
        inline=False,
    )
    return embed


def build_restored_embed(*, actor: Mentionable, channel: Mentionable) -> discord.Embed:
    """復元のチャンネル内の記録（移動の後に投稿する）"""
    return discord.Embed(
        title="復元",
        description=f"{actor.mention} が {channel.mention} を復元しました",
        color=discord.Color.green(),
    )


def build_restored_by_post_embed(*, author: Mentionable) -> discord.Embed:
    """投稿をきっかけにした自動復元のチャンネル内の記録（投稿した本人はそこにいるので通知しない）"""
    return discord.Embed(
        title="復元",
        description=f"{author.mention} の投稿で復元しました",
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
    prefix = f"{mention_label}: " if mention_label else ""
    chunks = _chunk_users(mention_users, MESSAGE_CONTENT_LIMIT - len(prefix))
    try:
        first = await channel.send(
            content=_mention_content(prefix, chunks[0]) if chunks else None,
            embed=embed,
            allowed_mentions=_only_users(chunks[0] if chunks else []),
        )
    except discord.HTTPException as e:
        logger.warning(f"Failed to post channel record: {e}")
        return None
    # 本文の上限を超える分は、続くメッセージでメンションする
    for chunk in chunks[1:]:
        try:
            await channel.send(
                content=_mention_content(prefix, chunk), allowed_mentions=_only_users(chunk)
            )
        except discord.HTTPException as e:
            logger.warning(f"Failed to post remaining mentions: {e}")
            break
    return first


def _chunk_users(users: Sequence[discord.abc.User], limit: int) -> list[list[discord.abc.User]]:
    """メンションをスペース区切りで並べたときに、limit文字に収まるよう分ける"""
    chunks: list[list[discord.abc.User]] = []
    length = 0
    for user in users:
        if chunks and length + 1 + len(user.mention) <= limit:
            chunks[-1].append(user)
            length += 1 + len(user.mention)
        else:
            chunks.append([user])
            length = len(user.mention)
    return chunks


def _mention_content(prefix: str, users: Sequence[discord.abc.User]) -> str:
    return prefix + " ".join(user.mention for user in users)


def _only_users(users: Sequence[discord.abc.User]) -> discord.AllowedMentions:
    return discord.AllowedMentions(everyone=False, users=list(users), roles=False)


async def delete_record(message: discord.Message) -> bool:
    """送った記録を消す。消せなかった場合はFalseを返す（例外は出さない）"""
    try:
        await message.delete()
    except discord.HTTPException as e:
        logger.warning(f"Failed to delete record: {e}")
        return False
    return True
