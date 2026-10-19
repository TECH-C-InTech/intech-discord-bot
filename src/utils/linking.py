"""番号によるチャンネルとロールの紐づけ"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import discord

from .kinds import Kind, kind_of_role_name
from .numbering import number_of, with_number


@dataclass(frozen=True)
class Linked:
    kind: Kind
    channel: discord.TextChannel
    role: discord.Role


@dataclass(frozen=True)
class Located:
    kind: Kind
    archived: bool


@dataclass(frozen=True)
class NotLinked:
    reason: str


def link_role(
    role: discord.Role,
    roles: Sequence[discord.Role],
    categories: Mapping[Kind, Sequence[discord.CategoryChannel]],
) -> Linked | NotLinked:
    """ロールと同じ番号のチャンネルを、種類のカテゴリ（通常とアーカイブ）から探す

    Args:
        role: 対象のロール
        roles: サーバーのすべてのロール（番号の重なりを確かめる）
        categories: 種類ごとの、チャンネルを置くカテゴリ（[通常, アーカイブ]の順）
    """
    kind = kind_of_role_name(role.name)
    if kind is None:
        return NotLinked(f"{role.mention} はクラブ・イベント・プロジェクトのロールではありません。")
    number = number_of(kind.prefix, role.name)
    assert number is not None
    same_number_roles = with_number(kind.prefix, number, roles, _name)
    if len(same_number_roles) > 1:
        return NotLinked(_mismatch(kind, number, "ロール", len(same_number_roles)))
    channels = [
        channel
        for category in categories.get(kind, [])
        for channel in with_number(kind.prefix, number, category.text_channels, _name)
    ]
    if len(channels) != 1:
        return NotLinked(_mismatch(kind, number, "チャンネル", len(channels)))
    return Linked(kind=kind, channel=channels[0], role=role)


def locate_channel(
    channel: discord.TextChannel,
    categories: Mapping[Kind, Sequence[discord.CategoryChannel]],
) -> Located | NotLinked:
    """チャンネルのあるカテゴリから、種類とアーカイブ中かどうかを返す

    Args:
        channel: 対象のチャンネル
        categories: 種類ごとの、チャンネルを置くカテゴリ（[通常, アーカイブ]の順）
    """
    for kind, kind_categories in categories.items():
        for index, category in enumerate(kind_categories):
            if category.id == channel.category_id:
                return Located(kind=kind, archived=index > 0)
    return NotLinked(
        f"{channel.mention} はクラブ・イベント・プロジェクトのチャンネルではありません。"
    )


def link_channel(
    channel: discord.TextChannel,
    roles: Sequence[discord.Role],
    categories: Mapping[Kind, Sequence[discord.CategoryChannel]],
) -> Linked | NotLinked:
    """チャンネルと同じ番号のロールを探す。種類はチャンネルのあるカテゴリで決まる

    Args:
        channel: 対象のチャンネル
        roles: サーバーのすべてのロール
        categories: 種類ごとの、チャンネルを置くカテゴリ
    """
    located = locate_channel(channel, categories)
    if isinstance(located, NotLinked):
        return located
    kind = located.kind
    number = number_of(kind.prefix, channel.name)
    if number is None:
        return NotLinked(
            f"{channel.mention} は{kind.label}チャンネルの形式"
            f"（{kind.prefix}001-xxx）ではありません。"
        )
    candidates = [
        role
        for role in with_number(kind.prefix, number, roles, _name)
        if kind.role_pattern.match(role.name)
    ]
    if len(candidates) != 1:
        return NotLinked(_mismatch(kind, number, "ロール", len(candidates)))
    # 見つかったロールからたどり直して、番号の重なりも同じように確かめる
    return link_role(candidates[0], roles, categories)


def _mismatch(kind: Kind, number: int, what: str, count: int) -> str:
    label = f"{kind.prefix}{number:03d}"
    if count == 0:
        return f"番号 `{label}` の{kind.label}の{what}が見つかりません。"
    # 手作業などで同じ番号が重なった場合は、どれを使うか決められないので止める
    return (
        f"番号 `{label}` の{kind.label}の{what}が{count}個あります。"
        "サーバー管理者に番号の重なりを直してもらってください。"
    )


def _name(item: discord.TextChannel | discord.Role) -> str:
    return item.name
