from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.commands.help import docs_impl, help_impl
from src.utils.command_metadata import CommandMetadata


async def sent_help() -> tuple[discord.Embed, dict]:
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.send_message = AsyncMock()

    await help_impl(interaction)

    interaction.response.send_message.assert_awaited_once()
    kwargs = interaction.response.send_message.await_args.kwargs
    return kwargs["embed"], kwargs


async def test_help_guides_by_what_members_want_to_do() -> None:
    embed, _ = await sent_help()

    assert embed.title == "🤖 InTechボットの使い方"
    assert [field.name for field in embed.fields] == [
        "🌱 操作可能なチャンネルの種類",
        "✨ チャンネルを作りたい",
        "🙋 イベント等に参加したい・抜けたい",
        "👥 イベント等にほかの人を追加したい・外したい",
        "📦 イベント等が終了したので片付けたい",
        "↩️ アーカイブ後にまた使いたい",
        "👀 イベント等に誰が参加しているか見たい",
    ]


async def test_help_does_not_list_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.utils.command_metadata._COMMAND_METADATA",
        {
            "setup_panel": CommandMetadata(category="パネル", short_description="設置する"),
            "create_channel": CommandMetadata(category="チャンネル管理", short_description="作成"),
        },
    )

    embed, _ = await sent_help()

    shown = "\n".join([embed.description or ""] + [field.value or "" for field in embed.fields])
    assert "/setup_panel" not in shown
    assert "/create_channel" not in shown


async def test_help_fits_discord_embed_limits() -> None:
    embed, _ = await sent_help()

    assert len(embed) <= 6000
    assert all(len(field.value or "") <= 1024 for field in embed.fields)


async def test_help_is_shown_only_to_the_member() -> None:
    _, kwargs = await sent_help()

    assert kwargs["ephemeral"] is True


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
