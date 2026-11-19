from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.commands.help import docs_impl, help_impl
from src.utils.command_metadata import CommandMetadata
from tests.ui_helpers import texts


async def sent_help(guild: discord.Guild | None = None) -> tuple[discord.ui.LayoutView, dict]:
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = guild
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.send_message = AsyncMock()

    await help_impl(interaction)

    interaction.response.send_message.assert_awaited_once()
    kwargs = interaction.response.send_message.await_args.kwargs
    return kwargs["view"], kwargs


def headings(view: discord.ui.LayoutView) -> list[str]:
    return [text.split("\n")[0] for text in texts(view) if text.startswith("#")]


def section_text(view: discord.ui.LayoutView, heading: str) -> str:
    return next(text for text in texts(view) if text.startswith(f"### {heading}"))


async def test_help_guides_by_what_members_want_to_do() -> None:
    view, _ = await sent_help()

    assert headings(view) == [
        "## 🤖 InTechボットの使い方",
        "### 🌱 操作可能なチャンネルの種類",
        "### ✨ チャンネルを作りたい",
        "### 🙋 参加したい・抜けたい",
        "### 👥 ほかの人を追加したい・外したい",
        "### 📦 終わったので片付けたい",
        "### ↩️ アーカイブ後にまた使いたい",
        "### 👀 誰が参加しているか見たい",
    ]


async def test_help_separates_each_section_with_a_line() -> None:
    view, _ = await sent_help()

    separators = [item for item in view.walk_children() if isinstance(item, discord.ui.Separator)]
    assert len(separators) >= len(headings(view)) - 1


async def test_help_does_not_list_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.utils.command_metadata._COMMAND_METADATA",
        {
            "setup_panel": CommandMetadata(category="パネル", short_description="設置する"),
            "create_channel": CommandMetadata(category="チャンネル管理", short_description="作成"),
        },
    )

    view, _ = await sent_help()

    shown = "\n".join(texts(view))
    assert "/setup_panel" not in shown
    assert "/create_channel" not in shown


async def test_help_fits_discord_text_limit() -> None:
    view, _ = await sent_help()

    # Components V2で1つのメッセージに出せる文字は合計4000字まで
    assert sum(len(text) for text in texts(view)) <= 4000


async def test_help_is_shown_only_to_the_member() -> None:
    _, kwargs = await sent_help()

    assert kwargs["ephemeral"] is True


async def test_help_links_to_create_channel_when_it_exists() -> None:
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = "create_channel"
    channel.mention = "<#123>"
    guild = MagicMock(spec=discord.Guild)
    guild.text_channels = [channel]

    view, _ = await sent_help(guild)

    text = section_text(view, "✨ チャンネルを作りたい")
    assert "<#123>" in text
    assert "#create_channel" not in text


async def test_help_names_create_channel_as_text_outside_a_server() -> None:
    view, _ = await sent_help(None)

    assert "#create_channel" in section_text(view, "✨ チャンネルを作りたい")


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
