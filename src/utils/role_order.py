"""作成したロールの置き場所（club > event > project の順に、種類ごとにまとめる）"""

from collections.abc import Iterable

from .kinds import KINDS

KIND_ORDER = [kind.key for kind in KINDS]
KIND_PATTERNS = {kind.key: kind.role_pattern for kind in KINDS}


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


def role_positions_after_move(
    roles: list[tuple[int, int]], *, role_id: int, target: int
) -> dict[int, int]:
    """ロールを target に動かしたときに、位置が変わるロールの新しい位置を返す

    roles は最新の (ID, 位置)。discord.pyのRole.edit(position=...)はキャッシュの位置で
    組み立てるため、作成直後でキャッシュにないロールを動かせない。そのため自前で組み立てる。
    """
    current = dict(roles)[role_id]
    low, high = min(current, target), max(current, target)
    between = sorted(
        (position, rid)
        for rid, position in roles
        if low <= position <= high and rid != role_id and position > 0
    )
    ordered = [rid for _, rid in between]
    # 上へ動かすなら間のロールは1つずつ下がり、下へ動かすなら1つずつ上がる
    ordered = [*ordered, role_id] if target > current else [role_id, *ordered]
    span = range(low, high + 1)
    if len(ordered) != len(span):
        # 位置が重複・欠番していると並びを決められないので、動かさない
        return {}
    return dict(zip(ordered, span, strict=True))


def display_ranks(roles: list[tuple[int, int]]) -> dict[int, int]:
    """(ID, 位置) から、画面上の並びどおりの順位（下から1, 2, …）を返す。@everyoneは除く

    Discordの位置は一意とは限らない（作成直後のロールは既存のロールと同じ位置になる）。
    同じ位置のロールはIDが大きいほうが下に表示されるので、それに合わせて振り直す。
    """
    ordered = sorted(
        ((position, -role_id, role_id) for role_id, position in roles if position > 0),
    )
    return {role_id: rank for rank, (_, _, role_id) in enumerate(ordered, start=1)}
