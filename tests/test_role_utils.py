from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.role_utils import (
    GrantResult,
    RevokeResult,
    describe_grant,
    describe_revoke,
    grant_role,
    revoke_role,
    with_creator,
)


def make_member(*roles: discord.Role) -> MagicMock:
    member = MagicMock(spec=discord.Member)
    member.roles = list(roles)
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
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


def member_with_id(member_id: int) -> MagicMock:
    member = make_member()
    member.id = member_id
    return member


def test_creator_is_added_as_first_participant() -> None:
    creator = member_with_id(1)
    other = member_with_id(2)

    assert with_creator([other], creator) == [creator, other]


def test_creator_listed_in_members_is_not_duplicated() -> None:
    creator = member_with_id(1)
    other = member_with_id(2)

    assert with_creator([other, member_with_id(1)], creator) == [creator, other]


def test_creator_who_is_not_a_server_member_is_not_added() -> None:
    other = member_with_id(2)
    creator = MagicMock(spec=discord.User)
    creator.id = 1

    assert with_creator([other], creator) == [other]


async def test_revokes_role_from_members_who_have_it() -> None:
    role = MagicMock(spec=discord.Role)
    member = make_member(role)

    result = await revoke_role([member], role)

    member.remove_roles.assert_awaited_once_with(role)
    assert result.revoked == [member]


async def test_members_without_role_are_separated_on_revoke() -> None:
    role = MagicMock(spec=discord.Role)
    member = make_member()

    result = await revoke_role([member], role)

    member.remove_roles.assert_not_called()
    assert result.revoked == []
    assert result.did_not_have == [member]


async def test_failed_members_are_separated_and_others_still_lose_role() -> None:
    role = MagicMock(spec=discord.Role)
    failing = make_member(role)
    failing.remove_roles = AsyncMock(
        side_effect=discord.Forbidden(MagicMock(status=403, reason="Forbidden"), "forbidden")
    )
    other = make_member(role)

    result = await revoke_role([failing, other], role)

    assert result.failed == [failing]
    assert result.revoked == [other]


def test_revoke_description_lists_each_group() -> None:
    result = RevokeResult(
        revoked=[mentioned("<@1>")], did_not_have=[mentioned("<@2>")], failed=[mentioned("<@3>")]
    )

    description = describe_revoke(result)
    assert "外しました:\n<@1>" in description
    assert "持っていません:\n<@2>" in description
    assert "外せませんでした:\n<@3>" in description
    assert "ロールの順位" in description
