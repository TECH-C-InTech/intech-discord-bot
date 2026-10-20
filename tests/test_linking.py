from collections.abc import Sequence
from unittest.mock import MagicMock

import discord

from src.utils.kinds import CLUB, EVENT, PROJECT, Kind
from src.utils.linking import (
    Linked,
    Located,
    NotLinked,
    collect_kind_categories,
    explain_not_linked,
    link_channel,
    link_role,
    locate_channel,
)


def make_channel(name: str, category_id: int) -> MagicMock:
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = name
    channel.category_id = category_id
    return channel


def make_category(category_id: int, *channel_names: str) -> MagicMock:
    category = MagicMock(spec=discord.CategoryChannel)
    category.id = category_id
    category.text_channels = [make_channel(name, category_id) for name in channel_names]
    return category


def make_role(name: str) -> MagicMock:
    role = MagicMock(spec=discord.Role)
    role.name = name
    return role


def categories(
    mapping: dict[str, Sequence[MagicMock]],
) -> "dict[Kind, Sequence[discord.CategoryChannel]]":
    kinds = {"club": CLUB, "event": EVENT}
    return {kinds[key]: value for key, value in mapping.items()}


def test_role_links_to_channel_with_same_number() -> None:
    events = make_category(1, "e011-a", "e012-おでん会")
    role = make_role("e012")

    linked = link_role(role, [role], categories({"event": [events]}))

    assert linked == Linked(kind=EVENT, channel=events.text_channels[1], role=role, archived=False)


def test_role_links_to_archived_channel() -> None:
    clubs = make_category(1, "c001-a")
    archived = make_category(2, "c005-ラーメン")
    role = make_role("c005-ラーメン")

    linked = link_role(role, [role], categories({"club": [clubs, archived]}))

    assert linked == Linked(kind=CLUB, channel=archived.text_channels[0], role=role, archived=True)


def test_role_without_channel_is_not_linked() -> None:
    role = make_role("e012")

    linked = link_role(role, [role], categories({"event": [make_category(1, "e011-a")]}))

    assert isinstance(linked, NotLinked)
    assert "e012" in linked.reason


def test_role_with_two_channels_of_same_number_is_not_linked() -> None:
    role = make_role("e012")
    events = make_category(1, "e012-a")
    archived = make_category(2, "e012-b")

    linked = link_role(role, [role], categories({"event": [events, archived]}))

    assert isinstance(linked, NotLinked)
    assert "2個" in linked.reason


def test_role_whose_number_is_shared_by_another_role_is_not_linked() -> None:
    role = make_role("c005-ラーメン")
    other = make_role("c005-つけ麺")
    clubs = make_category(1, "c005-ラーメン")

    linked = link_role(role, [role, other], categories({"club": [clubs]}))

    assert isinstance(linked, NotLinked)
    assert "ロールが2個" in linked.reason


def test_role_outside_kind_shapes_is_not_linked() -> None:
    role = make_role("運営")
    role.mention = "<@&9>"

    linked = link_role(role, [role], categories({"event": [make_category(1, "e001-a")]}))

    assert linked == NotLinked("<@&9> はクラブ・イベント・プロジェクトのロールではありません。")


def test_channel_links_to_role_with_same_number() -> None:
    clubs = make_category(1, "c001-a")
    archived = make_category(2, "c005-ラーメン")
    role = make_role("c005-ラーメン")
    channel = archived.text_channels[0]

    linked = link_channel(
        channel, [make_role("c001-a"), role], categories({"club": [clubs, archived]})
    )

    assert linked == Linked(kind=CLUB, channel=channel, role=role, archived=True)


def test_channel_outside_kind_categories_is_not_linked() -> None:
    channel = make_channel("雑談", category_id=99)

    linked = link_channel(channel, [], categories({"event": [make_category(1)]}))

    assert isinstance(linked, NotLinked)


def test_channel_without_number_is_not_linked() -> None:
    events = make_category(1, "おしらせ")

    linked = link_channel(events.text_channels[0], [], categories({"event": [events]}))

    assert isinstance(linked, NotLinked)


def test_channel_without_role_is_not_linked() -> None:
    events = make_category(1, "e012-おでん会")

    linked = link_channel(
        events.text_channels[0], [make_role("e011")], categories({"event": [events]})
    )

    assert isinstance(linked, NotLinked)
    assert "ロールが見つかりません" in linked.reason


def test_channel_in_archive_category_is_located_as_archived() -> None:
    clubs = make_category(1, "c001-a")
    archived = make_category(2, "c005-ラーメン")

    located = locate_channel(archived.text_channels[0], categories({"club": [clubs, archived]}))

    assert located == Located(kind=CLUB, archived=True)


def test_channel_in_own_category_is_located_as_not_archived() -> None:
    events = make_category(1, "e001-a")

    located = locate_channel(events.text_channels[0], categories({"event": [events]}))

    assert located == Located(kind=EVENT, archived=False)


def test_channel_in_shared_archive_is_located_by_its_number_prefix() -> None:
    # 設定でクラブとイベントのアーカイブカテゴリが同じになっている
    shared = make_category(3, "c005-ラーメン", "e003-おでん会")
    mapping = categories({"club": [make_category(1), shared], "event": [make_category(2), shared]})

    located = locate_channel(shared.text_channels[1], mapping)

    assert located == Located(kind=EVENT, archived=True)


def test_unnumbered_channel_in_shared_category_has_undecidable_kind() -> None:
    shared = make_category(3, "おしらせ")
    mapping = categories({"club": [make_category(1), shared], "event": [make_category(2), shared]})

    located = locate_channel(shared.text_channels[0], mapping)

    assert isinstance(located, NotLinked)
    assert "種類を決められません" in located.reason


def test_roles_outside_the_kind_shape_do_not_count_as_duplicates() -> None:
    role = make_role("c005-ラーメン")
    clubs = make_category(1, "c005-ラーメン")

    linked = link_role(role, [role, make_role("c005")], categories({"club": [clubs]}))

    assert linked == Linked(kind=CLUB, channel=clubs.text_channels[0], role=role, archived=False)


def named_category(category_id: int, name: str) -> MagicMock:
    category = make_category(category_id)
    category.name = name
    return category


def test_kind_without_its_own_category_is_left_out_and_reported() -> None:
    clubs, archived_clubs = named_category(1, "clubs"), named_category(2, "archived-clubs")
    names = {
        CLUB: ("clubs", "archived-clubs"),
        EVENT: ("events", "archived"),
        PROJECT: ("projects", "archived-projects"),
    }
    archived = named_category(3, "archived")

    mapping, missing = collect_kind_categories([clubs, archived_clubs, archived], names.__getitem__)

    assert mapping == {CLUB: [clubs, archived_clubs]}
    assert missing == ["events", "projects", "archived-projects"]


def test_not_linked_reason_mentions_missing_categories() -> None:
    reason = explain_not_linked(NotLinked("見つかりません。"), ["clubs"])

    assert reason.startswith("見つかりません。")
    assert "`clubs`" in reason


def test_not_linked_reason_is_kept_when_no_category_is_missing() -> None:
    assert explain_not_linked(NotLinked("見つかりません。"), []) == "見つかりません。"
