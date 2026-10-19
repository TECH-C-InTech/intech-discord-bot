from src.utils.club_name import validate_club_name


def validate(name: str) -> str | None:
    return validate_club_name(
        name,
        existing_role_names=["Administrator", "運営"],
        existing_channel_names=["ボドゲ"],
    )


def test_plain_name_is_allowed() -> None:
    assert validate("ラーメン") is None


def test_number_only_name_is_rejected() -> None:
    reason = validate("e001")
    assert reason is not None
    assert "番号" in reason


def test_uppercase_number_name_is_rejected() -> None:
    assert validate("E001") is not None


def test_number_with_name_is_rejected() -> None:
    assert validate("c012-x") is not None


def test_name_resembling_number_is_allowed() -> None:
    assert validate("e01") is None
    assert validate("e0012") is None


def test_existing_role_name_is_rejected() -> None:
    reason = validate("運営")
    assert reason is not None
    assert "ロール" in reason


def test_name_matching_existing_role_after_normalization_is_rejected() -> None:
    assert (
        validate_club_name(
            "Admin Team",
            existing_role_names=["admin-team"],
            existing_channel_names=[],
        )
        is not None
    )


def test_name_matching_existing_channel_after_normalization_is_rejected() -> None:
    reason = validate_club_name(
        "Board Games",
        existing_role_names=[],
        existing_channel_names=["board-games"],
    )
    assert reason is not None
    assert "チャンネル" in reason
