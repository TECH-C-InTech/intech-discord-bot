"""サンプルコマンド（テンプレート）

新しいコマンドを追加する際のテンプレートとして使用できます。
実際に使用する場合は、このファイルをコピーして新しいコマンドモジュールを作成してください。
"""

from logging import getLogger

import discord
from discord import app_commands

from ..utils.command_metadata import command_meta
from ..utils.env_utils import get_required_env  # noqa

logger = getLogger(__name__)


async def sample_command(ctx: discord.Interaction):
    """サンプルコマンドの実装"""
    await ctx.response.send_message("これはサンプルコマンドです！")


async def sample_command_with_args(ctx: discord.Interaction, message: str):
    """引数付きサンプルコマンドの実装"""
    await ctx.response.send_message(f"メッセージ: {message}")


def setup(tree: app_commands.CommandTree):
    """
    サンプルコマンドを登録する

    デコレーターの順序:
    1. @command_meta() - メタデータの登録（最上位）
    2. @tree.command() - コマンドの登録
    3. @app_commands.describe() - パラメータの説明
    4. @app_commands.choices() - 選択肢（必要な場合）
    """

    @command_meta(
        category="サンプル",
        icon="📝",
        short_description="基本的なサンプルコマンド",
        examples=["`/sample`"],
        notes="これはテンプレートです。実際のコマンドを実装する際の参考にしてください。",
    )
    @tree.command(name="sample", description="サンプルコマンド")
    async def sample_cmd(ctx: discord.Interaction):
        await sample_command(ctx)

    @command_meta(
        category="サンプル",
        icon="📝",
        short_description="引数を受け取るサンプルコマンド",
        examples=[
            "`/sample_with_args message:Hello`",
            "`/sample_with_args message:こんにちは`",
        ],
        notes="引数の説明は @app_commands.describe() で定義します。",
    )
    @tree.command(name="sample_with_args", description="引数付きサンプルコマンド")
    @app_commands.describe(message="表示するメッセージ")
    async def sample_with_args_cmd(ctx: discord.Interaction, message: str):
        await sample_command_with_args(ctx, message)
