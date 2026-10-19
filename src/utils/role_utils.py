"""ロールの付与"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from logging import getLogger

import discord

logger = getLogger(__name__)

GRANT_FAILURE_HELP = (
    "サーバー管理者に、botのロールが対象のロールより上にあり（ロールの順位）、"
    "「ロールの管理」権限があるか確認してもらってください。"
)


@dataclass
class GrantResult:
    """メンバーごとのロール付与の結果"""

    granted: list[discord.Member] = field(default_factory=list)
    already_had: list[discord.Member] = field(default_factory=list)
    failed: list[discord.Member] = field(default_factory=list)


async def grant_role(members: Sequence[discord.Member], role: discord.Role) -> GrantResult:
    """メンバーにロールを付与する。失敗した人がいても残りの人への付与は続ける"""
    result = GrantResult()
    for member in members:
        if role in member.roles:
            result.already_had.append(member)
            continue
        try:
            await member.add_roles(role)
        except discord.HTTPException as e:
            logger.warning(f"Failed to add role {role} to {member}: {e}")
            result.failed.append(member)
            continue
        result.granted.append(member)
    return result


def _mentions(members: Sequence[discord.Member]) -> str:
    return ", ".join(member.mention for member in members)


def describe_grant(result: GrantResult) -> str:
    """付与の結果を、本人への返信に使う説明文にする"""
    parts = []
    if result.granted:
        parts.append(f"以下のメンバーにロールを付与しました:\n{_mentions(result.granted)}")
    if result.already_had:
        parts.append(f"以下のメンバーは既にロールを持っています:\n{_mentions(result.already_had)}")
    if result.failed:
        parts.append(
            f"以下のメンバーにはロールを付与できませんでした:\n{_mentions(result.failed)}\n"
            f"{GRANT_FAILURE_HELP}"
        )
    return "\n".join(parts)
