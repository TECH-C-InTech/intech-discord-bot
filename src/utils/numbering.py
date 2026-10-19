"""番号（c001 / e001 / p001）の採番と読み取り"""

from collections.abc import Callable, Iterable
import re
from typing import TypeVar

T = TypeVar("T")

MAX_NUMBER = 999
NUMBERS_EXHAUSTED = (
    "番号が上限（999）に達したため、これ以上作成できません。サーバー管理者に連絡してください。"
)


def number_of(prefix: str, name: str) -> int | None:
    """名前の先頭の番号を返す（c005-ラーメン → 5）。その種類の番号がなければNone"""
    match = re.match(rf"^{re.escape(prefix)}(\d{{3}})(-|$)", name)
    return int(match.group(1)) if match else None


def next_number(prefix: str, names: Iterable[str]) -> int | None:
    """使われている最大の番号に1を足す。欠番は埋めない（番号は再利用しない）

    番号は3桁なので、999まで使い切っていたらNoneを返す。
    """
    numbers = [n for n in (number_of(prefix, name) for name in names) if n is not None]
    number = max(numbers, default=0) + 1
    return number if number <= MAX_NUMBER else None


def with_number(prefix: str, number: int, items: Iterable[T], name: Callable[[T], str]) -> list[T]:
    """名前の番号が number のものをすべて返す（同じ番号が重なっていないか呼び出し側で確かめる）"""
    return [item for item in items if number_of(prefix, name(item)) == number]
