"""サンプルコマンド（テンプレート）

新しいコマンドを追加する際のテンプレートとして使用できます。
実際に使用する場合は、このファイルをコピーして新しいコマンドモジュールを作成してください。
"""

from logging import getLogger

import discord
from discord import app_commands

from ..utils.env_utils import get_required_env

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

    このsetup関数は、src/commands/__init__.pyのCOMMAND_MODULESリストに
    このモジュールを追加することで自動的に呼び出されます。
    """

    @tree.command(name="sample", description="サンプルコマンド")
    async def sample_cmd(ctx: discord.Interaction):
        await sample_command(ctx)

    @tree.command(name="sample_with_args", description="引数付きサンプルコマンド")
    @app_commands.describe(message="表示するメッセージ")
    async def sample_with_args_cmd(ctx: discord.Interaction, message: str):
        await sample_command_with_args(ctx, message)
