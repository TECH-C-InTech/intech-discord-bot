"""Discordの上限に対する残量の計算と判定

Discordオブジェクトに依存せず、件数だけを受け取る。件数は呼び出し側でキャッシュから数える。
"""

from dataclasses import dataclass

CATEGORY_CHANNEL_LIMIT = 50
GUILD_CHANNEL_LIMIT = 500  # カテゴリも1件として数える
GUILD_ROLE_LIMIT = 250


@dataclass(frozen=True)
class Capacity:
    """上限までの残り件数"""

    category_channels: int
    guild_channels: int
    guild_roles: int


def remaining_capacity(
    *, category_channels: int, guild_channels: int, guild_roles: int
) -> Capacity:
    """現在の件数から、上限までの残り件数を計算する

    Args:
        category_channels: 対象カテゴリ内のチャンネル数
        guild_channels: サーバーのチャンネル数（カテゴリ込み）
        guild_roles: サーバーのロール数（@everyone込み）
    """
    return Capacity(
        category_channels=CATEGORY_CHANNEL_LIMIT - category_channels,
        guild_channels=GUILD_CHANNEL_LIMIT - guild_channels,
        guild_roles=GUILD_ROLE_LIMIT - guild_roles,
    )


def check_creation_capacity(
    *, category_channels: int, guild_channels: int, guild_roles: int
) -> str | None:
    """チャンネルとロールを1つずつ作れるか判定する

    Returns:
        作れない場合はその理由。作れる場合はNone
    """
    remaining = remaining_capacity(
        category_channels=category_channels,
        guild_channels=guild_channels,
        guild_roles=guild_roles,
    )
    if remaining.category_channels <= 0:
        return f"カテゴリのチャンネル数が上限（{CATEGORY_CHANNEL_LIMIT}）に達しています。"
    if remaining.guild_channels <= 0:
        return f"サーバーのチャンネル数が上限（{GUILD_CHANNEL_LIMIT}）に達しています。"
    if remaining.guild_roles <= 0:
        return f"サーバーのロール数が上限（{GUILD_ROLE_LIMIT}）に達しています。"
    return None


def check_move_capacity(*, destination_category_channels: int) -> str | None:
    """移動先カテゴリにチャンネルを1つ移せるか判定する

    Returns:
        移せない場合はその理由。移せる場合はNone
    """
    if CATEGORY_CHANNEL_LIMIT - destination_category_channels <= 0:
        return f"移動先カテゴリのチャンネル数が上限（{CATEGORY_CHANNEL_LIMIT}）に達しています。"
    return None
