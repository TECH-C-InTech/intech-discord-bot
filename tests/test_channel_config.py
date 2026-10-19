from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.utils.channel_config import ChannelConfig

REQUIRED_ENV = {
    "EVENT_CATEGORY_NAME": "events",
    "ARCHIVE_EVENT_CATEGORY_NAME": "archived",
    "PROJECT_CATEGORY_NAME": "projects",
    "ARCHIVE_PROJECT_CATEGORY_NAME": "archived-projects",
    "CLUB_CATEGORY_NAME": "clubs",
    "LOG_CHANNEL_NAME": "bot-log",
}


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    ChannelConfig._instance = None
    yield
    ChannelConfig._instance = None


def test_config_cannot_be_loaded_without_log_channel_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_CHANNEL_NAME")

    assert ChannelConfig.get_instance() is None


async def test_load_error_lists_only_missing_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_CHANNEL_NAME")
    ctx = MagicMock(spec=discord.Interaction)
    ctx.response = MagicMock()
    ctx.response.send_message = AsyncMock()

    assert await ChannelConfig.load(ctx) is None

    message = ctx.response.send_message.await_args.args[0]
    assert "LOG_CHANNEL_NAME" in message
    assert "EVENT_CATEGORY_NAME" not in message
