"""環境変数関連のユーティリティ"""

import os
from typing import Optional

import discord


def get_required_env(key: str) -> Optional[str]:
    """
    環境変数を取得する

    Args:
        key: 環境変数のキー

    Returns:
        環境変数の値。存在しない場合はNone
    """
    return os.getenv(key)


async def validate_env_and_respond(
    ctx: discord.Interaction, key: str
) -> Optional[str]:
    """
    環境変数を取得し、存在しない場合はエラーメッセージを返す

    Args:
        ctx: Discord Interaction
        key: 環境変数のキー

    Returns:
        環境変数の値。存在しない場合はNoneを返し、エラーメッセージを送信する
    """
    value = get_required_env(key)
    if not value:
        await ctx.response.send_message(
            f"❌ 環境変数 '{key}' が設定されていません。", ephemeral=True
        )
    return value
