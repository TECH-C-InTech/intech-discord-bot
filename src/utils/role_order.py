"""作成したロールの置き場所（club > event > project の順に、種類ごとにまとめる）"""

from collections.abc import Iterable
import re

KIND_ORDER = ["club", "event", "project"]
KIND_PATTERNS = {
    "club": re.compile(r"^c\d{3}-"),
    "event": re.compile(r"^e\d{3}$"),
    "project": re.compile(r"^p\d{3}$"),
}


def target_role_position(kind: str, roles: Iterable[tuple[str, int]]) -> int | None:
    roles = list(roles)
    own = [position for name, position in roles if KIND_PATTERNS[kind].match(name)]
    if own:
        return min(own) - 1
    lower_kinds = KIND_ORDER[KIND_ORDER.index(kind) + 1 :]
    lower = [
        position
        for name, position in roles
        if any(KIND_PATTERNS[lower_kind].match(name) for lower_kind in lower_kinds)
    ]
    if lower:
        return max(lower)
    return None
