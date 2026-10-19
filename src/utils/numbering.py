"""番号（c001 / e001 / p001）の採番と読み取り"""

from collections.abc import Iterable
import re


def number_of(prefix: str, name: str) -> int | None:
    """名前の先頭の番号を返す（c005-ラーメン → 5）。その種類の番号がなければNone"""
    match = re.match(rf"^{prefix}(\d{{3}})(-|$)", name)
    return int(match.group(1)) if match else None


def next_number(prefix: str, names: Iterable[str]) -> int:
    """使われている最大の番号に1を足す。欠番は埋めない（番号は再利用しない）"""
    numbers = [n for n in (number_of(prefix, name) for name in names) if n is not None]
    return max(numbers, default=0) + 1
