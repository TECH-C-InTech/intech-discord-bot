"""ロールの付与"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from logging import getLogger

import discord

logger = getLogger(__name__)


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
