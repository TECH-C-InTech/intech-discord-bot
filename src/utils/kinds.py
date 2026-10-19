"""チャンネルの種類（クラブ・イベント・プロジェクト）ごとの違い"""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Kind:
    key: str
    prefix: str
    label: str
    role_pattern: re.Pattern[str]
    # ロール名にチャンネルの名前も含めるか（クラブは常設なので、メンションで何か分かるように）
    role_includes_name: bool = False

    def channel_name(self, number: int, name: str) -> str:
        return f"{self.prefix}{number:03d}-{name}"

    def role_name(self, channel_name: str) -> str:
        if self.role_includes_name:
            return channel_name
        return channel_name.split("-", 1)[0]


CLUB = Kind(
    key="club",
    prefix="c",
    label="クラブ",
    role_pattern=re.compile(r"^c\d{3}-"),
    role_includes_name=True,
)
EVENT = Kind(key="event", prefix="e", label="イベント", role_pattern=re.compile(r"^e\d{3}$"))
PROJECT = Kind(
    key="project", prefix="p", label="プロジェクト", role_pattern=re.compile(r"^p\d{3}$")
)

KINDS = (CLUB, EVENT, PROJECT)


def kind_of_role_name(name: str) -> Kind | None:
    """ロール名の形から種類を返す。どの種類のロールでもなければNone"""
    return next((kind for kind in KINDS if kind.role_pattern.match(name)), None)
