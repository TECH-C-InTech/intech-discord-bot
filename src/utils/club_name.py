"""クラブチャンネル名の検証

クラブはチャンネルとロールを名前で結びつけるため、既存のロールや番号つきのロール、
ログチャンネルと衝突する名前を作らせない。
"""

from collections.abc import Iterable
import re

NUMBERED_NAME_PATTERN = re.compile(r"^[cep]\d{3}(-|$)")


def normalize_channel_name(name: str) -> str:
    """Discordがテキストチャンネル名に行う正規化を近似する（小文字化、空白をハイフンに）

    Discordの正規化規則は公開されていないため、作成後の実際の名前でも検証し直すこと。
    """
    return re.sub(r"\s+", "-", name.strip()).lower()


def validate_club_name(
    name: str,
    *,
    log_channel_name: str,
    existing_role_names: Iterable[str],
    existing_channel_names: Iterable[str],
) -> str | None:
    """クラブチャンネル名として使えるか判定する

    Args:
        name: 検証する名前（入力そのまま、または作成されたチャンネルの名前）
        log_channel_name: ログチャンネル名
        existing_role_names: サーバーのロール名
        existing_channel_names: 同じカテゴリにある、検証対象以外のチャンネル名

    Returns:
        使えない場合はその理由。使える場合はNone
    """
    normalized = normalize_channel_name(name)
    if NUMBERED_NAME_PATTERN.match(normalized):
        return "番号と同じ形式の名前は使えません。"
    if normalized == normalize_channel_name(log_channel_name):
        return "ログチャンネルと同じ名前は使えません。"
    role_names = set(existing_role_names)
    if name in role_names or normalized in role_names:
        return "既存のロールと同じ名前は使えません。"
    if normalized in existing_channel_names:
        return "同じ名前のチャンネルが既にあります。"
    return None
