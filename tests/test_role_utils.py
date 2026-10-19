from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.role_utils import grant_role


def make_member(*roles: discord.Role) -> MagicMock:
    member = MagicMock(spec=discord.Member)
    member.roles = list(roles)
    member.add_roles = AsyncMock()
    return member


async def test_grants_role_to_members_without_it() -> None:
    role = MagicMock(spec=discord.Role)
    member = make_member()

    result = await grant_role([member], role)

    member.add_roles.assert_awaited_once_with(role)
    assert result.granted == [member]


async def test_members_who_already_have_role_are_separated() -> None:
    role = MagicMock(spec=discord.Role)
    member = make_member(role)

    result = await grant_role([member], role)

    member.add_roles.assert_not_called()
    assert result.granted == []
    assert result.already_had == [member]


async def test_failed_members_are_separated_and_others_still_get_role() -> None:
    role = MagicMock(spec=discord.Role)
    failing = make_member()
    failing.add_roles = AsyncMock(
        side_effect=discord.Forbidden(MagicMock(status=403, reason="Forbidden"), "forbidden")
    )
    other = make_member()

    result = await grant_role([failing, other], role)

    assert result.failed == [failing]
    assert result.granted == [other]
