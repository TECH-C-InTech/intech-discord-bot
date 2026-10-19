import pytest

from src.utils.kinds import CLUB, EVENT, PROJECT, Kind, kind_of_role_name


@pytest.mark.parametrize(
    ("name", "kind"), [("c005-ラーメン", CLUB), ("e012", EVENT), ("p004", PROJECT)]
)
def test_role_name_tells_its_kind(name: str, kind: object) -> None:
    assert kind_of_role_name(name) is kind


@pytest.mark.parametrize("name", ["c005", "e012-x", "運営", "p0041"])
def test_names_outside_the_shapes_are_not_kind_roles(name: str) -> None:
    assert kind_of_role_name(name) is None


def test_club_role_is_named_after_its_channel() -> None:
    channel_name = CLUB.channel_name(5, "ラーメン")

    assert channel_name == "c005-ラーメン"
    assert CLUB.role_name(channel_name) == "c005-ラーメン"


@pytest.mark.parametrize(("kind", "role"), [(EVENT, "e012"), (PROJECT, "p012")])
def test_event_and_project_roles_are_just_the_number(kind: Kind, role: str) -> None:
    assert kind.role_name(kind.channel_name(12, "おでん-会")) == role
