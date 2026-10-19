from collections.abc import Iterator
import re
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.utils.channel_config import ChannelConfig
from src.utils.kinds import CLUB, EVENT, PROJECT, Kind

REQUIRED_ENV = {
    "EVENT_CATEGORY_NAME": "events",
    "ARCHIVE_EVENT_CATEGORY_NAME": "archived",
    "PROJECT_CATEGORY_NAME": "projects",
    "ARCHIVE_PROJECT_CATEGORY_NAME": "archived-projects",
    "CLUB_CATEGORY_NAME": "clubs",
    "ARCHIVE_CLUB_CATEGORY_NAME": "archived-clubs",
}


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    ChannelConfig._instance = None
    yield
    ChannelConfig._instance = None


def test_config_cannot_be_loaded_without_required_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLUB_CATEGORY_NAME")

    assert ChannelConfig.get_instance() is None


async def test_load_error_lists_only_missing_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLUB_CATEGORY_NAME")
    ctx = MagicMock(spec=discord.Interaction)
    ctx.response = MagicMock()
    ctx.response.send_message = AsyncMock()

    assert await ChannelConfig.load(ctx) is None

    message = ctx.response.send_message.await_args.args[0]
    assert "CLUB_CATEGORY_NAME" in message
    assert "EVENT_CATEGORY_NAME" not in message


def test_config_cannot_be_loaded_without_club_archive_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ARCHIVE_CLUB_CATEGORY_NAME")

    assert ChannelConfig.get_instance() is None


def test_each_kind_has_its_own_and_archive_category() -> None:
    config = ChannelConfig.get_instance()
    assert config is not None

    assert config.category_names(CLUB) == ("clubs", "archived-clubs")
    assert config.category_names(EVENT) == ("events", "archived")
    assert config.category_names(PROJECT) == ("projects", "archived-projects")


def test_unknown_kind_has_no_categories() -> None:
    config = ChannelConfig.get_instance()
    assert config is not None
    other = Kind(key="other", prefix="o", label="その他", role_pattern=re.compile(r"^o\d{3}$"))

    with pytest.raises(KeyError):
        config.category_names(other)
