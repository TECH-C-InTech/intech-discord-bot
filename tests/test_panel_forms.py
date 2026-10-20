from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.utils.kinds import EVENT
from src.utils.linking import Linked
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


def config_of(names: dict[str, tuple[str, str]]) -> MagicMock:
    config = MagicMock()
    config.category_names = MagicMock(side_effect=lambda kind: names[kind.key])
    return config


def guild_where_channel_is_archived(
    role_permissions: discord.Permissions | None = None,
) -> tuple[MagicMock, Linked]:
    """フォームを開いたときは通常のカテゴリにあったが、今はアーカイブされているチャンネル"""
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = "e003-おでん会"
    channel.category_id = 2
    events = MagicMock(spec=discord.CategoryChannel)
    events.id, events.name, events.text_channels = 1, "events", []
    archived = MagicMock(spec=discord.CategoryChannel)
    archived.id, archived.name, archived.text_channels = 2, "archived", [channel]
    role = MagicMock(spec=discord.Role)
    role.name = "e003"
    role.permissions = role_permissions or discord.Permissions.none()
    role.managed = False
    role.is_default = MagicMock(return_value=False)
    guild = MagicMock(spec=discord.Guild)
    guild.categories = [events, archived]
    guild.roles = [role]
    return guild, Linked(kind=EVENT, channel=channel, role=role, archived=False)


async def test_add_form_asks_at_least_one_person() -> None:
    form = ParticipantsForm(MagicMock(), linked_channel(), removing=False)

    assert form.title == "参加者を追加"
    assert fields(form) == [("追加する人", "#e003-おでん会 に追加します")]
    assert form.people.min_values == 1


async def test_remove_form_says_whom_to_remove_from() -> None:
    form = ParticipantsForm(MagicMock(), linked_channel(), removing=True)

    assert form.title == "参加者を外す"
    assert fields(form) == [("外す人", "#e003-おでん会 から外します")]


async def test_participants_form_uses_channel_state_at_submit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remove = AsyncMock()
    monkeypatch.setattr("src.utils.panel_forms.remove_participants", remove)
    member = MagicMock(spec=discord.Member)
    selecting(monkeypatch, member)
    guild, opened = guild_where_channel_is_archived()
    config = config_of(
        {"club": ("c", "ac"), "event": ("events", "archived"), "project": ("p", "ap")}
    )
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = guild

    await ParticipantsForm(config, opened, removing=True).on_submit(interaction)

    assert remove.await_args is not None
    _, linked, members = remove.await_args.args
    assert linked.archived is True
    assert members == [member]


async def test_participants_form_checks_role_safety_at_submit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # フォームを開いている間に、ロールが管理者権限を持つものに変わっていることがある
    add = AsyncMock()
    monkeypatch.setattr("src.utils.panel_forms.add_participants", add)
    selecting(monkeypatch, MagicMock(spec=discord.Member))
    guild, opened = guild_where_channel_is_archived(discord.Permissions(administrator=True))
    config = config_of(
        {"club": ("c", "ac"), "event": ("events", "archived"), "project": ("p", "ap")}
    )
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = guild
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.send_message = AsyncMock()

    await ParticipantsForm(config, opened, removing=False).on_submit(interaction)

    add.assert_not_called()
    interaction.response.send_message.assert_awaited_once()
