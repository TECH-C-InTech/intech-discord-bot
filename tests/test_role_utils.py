from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.role_utils import GrantResult, describe_grant, grant_role


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


def mentioned(mention: str) -> MagicMock:
    member = make_member()
    member.mention = mention
    return member


def test_description_lists_granted_members() -> None:
    result = GrantResult(granted=[mentioned("<@1>"), mentioned("<@2>")])

    assert "<@1>, <@2>" in describe_grant(result)


def test_description_lists_members_who_already_had_role() -> None:
    result = GrantResult(already_had=[mentioned("<@3>")])

    assert "既にロールを持っています" in describe_grant(result)
    assert "<@3>" in describe_grant(result)


def test_description_lists_failed_members_with_how_to_fix() -> None:
    result = GrantResult(failed=[mentioned("<@4>")])

    description = describe_grant(result)
    assert "<@4>" in description
    assert "ロールの順位" in description


def test_description_is_empty_without_members() -> None:
    assert describe_grant(GrantResult()) == ""
