import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.creation import Created, Failed, Rejected, create_channel_with_role


def http_error() -> discord.HTTPException:
    return discord.HTTPException(MagicMock(status=500, reason="error"), "error")


def make_guild(
    *, category_channels: int = 0, guild_channels: int = 0, guild_roles: int = 1
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    guild = MagicMock(spec=discord.Guild)
    category = MagicMock(spec=discord.CategoryChannel)
    category.channels = [MagicMock() for _ in range(category_channels)]
    guild.channels = [MagicMock() for _ in range(guild_channels)]
    guild.roles = [MagicMock() for _ in range(guild_roles)]
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = "e001-おでん会"
    channel.delete = AsyncMock()
    role = MagicMock(spec=discord.Role)
    role.id = 42
    guild.create_text_channel = AsyncMock(return_value=channel)
    guild.create_role = AsyncMock(return_value=role)
    guild.get_role = MagicMock(return_value=role)
    return guild, category, channel, role


async def create(
    guild: MagicMock, category: MagicMock, **overrides: Any
) -> Created | Rejected | Failed:
    kwargs: dict[str, Any] = {
        "decide_name": lambda guild, category: "e001-おでん会",
        "role_name_for": lambda channel: "e001",
        "lock": asyncio.Lock(),
        "pending_role_ids": {},
    }
    kwargs.update(overrides)
    return await create_channel_with_role(guild, category, **kwargs)


async def test_rejects_without_creating_anything_when_capacity_is_exceeded() -> None:
    guild, category, _, _ = make_guild(category_channels=50)

    outcome = await create(guild, category)

    assert isinstance(outcome, Rejected)
    guild.create_text_channel.assert_not_called()
    guild.create_role.assert_not_called()


async def test_rejects_without_creating_anything_when_name_is_rejected() -> None:
    guild, category, _, _ = make_guild()

    outcome = await create(guild, category, decide_name=lambda g, c: Rejected("同名あり"))

    assert outcome == Rejected("同名あり")
    guild.create_text_channel.assert_not_called()


async def test_creates_channel_and_mentionable_role() -> None:
    guild, category, channel, role = make_guild()

    outcome = await create(guild, category)

    assert outcome == Created(channel=channel, role=role)
    guild.create_text_channel.assert_awaited_once_with(name="e001-おでん会", category=category)
    guild.create_role.assert_awaited_once_with(name="e001", mentionable=True)


async def test_fails_without_creating_role_when_channel_creation_fails() -> None:
    guild, category, _, _ = make_guild()
    error = http_error()
    guild.create_text_channel = AsyncMock(side_effect=error)

    outcome = await create(guild, category)

    assert outcome == Failed(error=error, leftover_channel=None)
    guild.create_role.assert_not_called()


async def test_deletes_channel_when_role_creation_fails() -> None:
    guild, category, channel, _ = make_guild()
    error = http_error()
    guild.create_role = AsyncMock(side_effect=error)

    outcome = await create(guild, category)

    assert outcome == Failed(error=error, leftover_channel=None)
    channel.delete.assert_awaited_once()


async def test_reports_leftover_channel_when_rollback_after_role_failure_fails() -> None:
    guild, category, channel, _ = make_guild()
    role_error = http_error()
    guild.create_role = AsyncMock(side_effect=role_error)
    channel.delete = AsyncMock(side_effect=http_error())

    outcome = await create(guild, category)

    assert outcome == Failed(error=role_error, leftover_channel=channel)


async def test_concurrent_creations_run_one_at_a_time() -> None:
    guild, category, channel, _ = make_guild()
    lock = asyncio.Lock()
    release_first = asyncio.Event()
    names_decided: list[str] = []

    async def slow_create_text_channel(**kwargs: object) -> MagicMock:
        await release_first.wait()
        return channel

    guild.create_text_channel = AsyncMock(side_effect=slow_create_text_channel)

    def decide(label: str) -> Callable[[discord.Guild, discord.CategoryChannel], str]:
        def _decide(g: discord.Guild, c: discord.CategoryChannel) -> str:
            names_decided.append(label)
            return label

        return _decide

    first = asyncio.create_task(create(guild, category, decide_name=decide("first"), lock=lock))
    await asyncio.sleep(0.01)
    second = asyncio.create_task(create(guild, category, decide_name=decide("second"), lock=lock))
    await asyncio.sleep(0.01)

    assert names_decided == ["first"]

    release_first.set()
    await asyncio.gather(first, second)

    assert names_decided == ["first", "second"]


async def test_role_not_yet_in_cache_is_counted_by_next_capacity_check() -> None:
    guild, category, _, _ = make_guild(guild_roles=249)
    guild.get_role = MagicMock(return_value=None)
    pending: dict[int, set[int]] = {}

    first = await create(guild, category, pending_role_ids=pending)
    second = await create(guild, category, pending_role_ids=pending)

    assert isinstance(first, Created)
    assert isinstance(second, Rejected)


async def test_role_that_appeared_in_cache_is_not_counted_twice() -> None:
    guild, category, _, role = make_guild(guild_roles=248)
    pending: dict[int, set[int]] = {}
    guild.get_role = MagicMock(return_value=role)

    await create(guild, category, pending_role_ids=pending)
    # 作成したロールがキャッシュ（guild.roles）に入った
    guild.roles.append(role)
    second = await create(guild, category, pending_role_ids=pending)

    assert isinstance(second, Created)


def named_role(name: str, position: int, role_id: int) -> MagicMock:
    role = MagicMock(spec=discord.Role)
    role.name = name
    role.position = position
    role.id = role_id
    return role


async def test_created_role_is_moved_next_to_roles_of_its_kind() -> None:
    guild, category, _, role = make_guild()
    role.edit = AsyncMock()
    guild.roles = [named_role("e002", 5, 1), named_role("p001", 4, 2), role]

    await create(guild, category, role_kind="event")

    role.edit.assert_awaited_once_with(position=4)


async def test_failing_to_move_role_does_not_fail_creation() -> None:
    guild, category, channel, role = make_guild()
    role.edit = AsyncMock(side_effect=http_error())
    guild.roles = [named_role("e002", 5, 1), role]

    outcome = await create(guild, category, role_kind="event")

    assert outcome == Created(channel=channel, role=role)
