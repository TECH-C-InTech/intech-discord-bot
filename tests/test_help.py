from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.commands.help import build_help_view, docs_impl, help_impl
from src.utils.command_metadata import CommandMetadata
from tests.ui_helpers import texts


def guild_with_channel(name: str, mention: str) -> discord.Guild:
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = name
    channel.mention = mention
    guild = MagicMock(spec=discord.Guild)
    guild.text_channels = [channel]
    return guild


def create_section(view: discord.ui.LayoutView) -> str:
    return next(text for text in texts(view) if "作りたい" in text.split("\n")[0])


def test_help_starts_with_title_then_sections_with_body() -> None:
    title, *sections, footer = texts(build_help_view(None))

    assert title.startswith("## ")
    assert sections
    for section in sections:
        heading, _, body = section.partition("\n")
        assert heading.startswith("### ")
        assert body.strip()
    assert "/docs" in footer


def test_help_fits_discord_message_limits() -> None:
    view = build_help_view(None)

    # 1つのメッセージに出せるのは、文字の部品の合計4000字まで、部品は40個まで
    assert sum(len(text) for text in texts(view)) <= 4000
    assert len(list(view.walk_children())) <= 40


def test_help_links_to_create_channel_when_it_exists() -> None:
    view = build_help_view(guild_with_channel("create_channel", "<#123>"))

    section = create_section(view)
    assert "<#123>" in section
    assert "#create_channel" not in section


def test_help_names_create_channel_as_text_when_it_is_missing() -> None:
    view = build_help_view(guild_with_channel("general", "<#456>"))

    assert "#create_channel" in create_section(view)


def test_help_names_create_channel_as_text_outside_a_server() -> None:
    assert "#create_channel" in create_section(build_help_view(None))


async def test_help_is_shown_only_to_the_member() -> None:
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = None
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.send_message = AsyncMock()

    await help_impl(interaction)

    assert interaction.response.send_message.await_args.kwargs["ephemeral"] is True


async def test_docs_list_shows_short_description_of_each_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.utils.command_metadata._COMMAND_METADATA",
        {"intech": CommandMetadata(category="パネル", short_description="パネルを出す")},
    )
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.send_message = AsyncMock()

    await docs_impl(MagicMock(), interaction)

    embed = interaction.response.send_message.await_args.kwargs["embed"]
    assert embed.fields[0].value == "• `/docs command:intech` - パネルを出す"
