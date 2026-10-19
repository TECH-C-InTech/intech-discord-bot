from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.utils.kinds import EVENT
from src.utils.panel_forms import CreateForm, ParticipantsForm


def fields(form: discord.ui.Modal) -> list[tuple[str, str | None]]:
    return [(label.text, label.description) for label in form.children]  # type: ignore[attr-defined]


async def test_create_form_asks_name_and_other_participants() -> None:
    form = CreateForm(MagicMock(), EVENT, next_number="e013")

    assert form.title == "イベントを作る"
    assert fields(form) == [
        ("イベント名", "番号（e013 など）は自動で付きます"),
        ("他の参加者（任意）", None),
    ]
    assert form.name.placeholder == "例: おでん会"
    assert form.others.required is False


def selecting(monkeypatch: pytest.MonkeyPatch, *users: object) -> None:
    monkeypatch.setattr(discord.ui.UserSelect, "values", property(lambda _: list(users)))


async def test_create_form_creates_channel_with_selected_members(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = AsyncMock()
    monkeypatch.setattr("src.utils.panel_forms.create", create)
    member = MagicMock(spec=discord.Member)
    selecting(monkeypatch, member)
    config = MagicMock()
    form = CreateForm(config, EVENT, next_number="e013")
    form.name._value = "おでん会"
    interaction = MagicMock(spec=discord.Interaction)

    await form.on_submit(interaction)

    create.assert_awaited_once_with(interaction, config, EVENT, "おでん会", [member])


def linked_channel() -> MagicMock:
    linked = MagicMock()
    linked.channel.name = "e003-おでん会"
    return linked


async def test_add_form_asks_at_least_one_person() -> None:
    form = ParticipantsForm(linked_channel(), removing=False)

    assert form.title == "参加者を追加"
    assert fields(form) == [("追加する人", "#e003-おでん会 に追加します")]
    assert form.people.min_values == 1


async def test_remove_form_says_whom_to_remove_from() -> None:
    form = ParticipantsForm(linked_channel(), removing=True)

    assert form.title == "参加者を外す"
    assert fields(form) == [("外す人", "#e003-おでん会 から外します")]


async def test_participants_form_removes_selected_members(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remove = AsyncMock()
    monkeypatch.setattr("src.utils.panel_forms.remove_participants", remove)
    member = MagicMock(spec=discord.Member)
    selecting(monkeypatch, member)
    linked = linked_channel()
    interaction = MagicMock(spec=discord.Interaction)

    await ParticipantsForm(linked, removing=True).on_submit(interaction)

    remove.assert_awaited_once_with(interaction, linked, [member])
