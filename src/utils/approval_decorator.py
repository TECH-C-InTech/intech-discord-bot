"""承認ミドルウェア用のデコレーター."""

from collections.abc import Callable
from functools import wraps
from logging import getLogger
from typing import Any

import discord

from src.utils.approval_config import ApprovalConfig
from src.utils.approval_utils import (
    create_approval_request_embed,
    has_approver_role,
)
from src.views.approval_view import ApprovalView

logger = getLogger(__name__)


def require_approval(
    timeout_hours: int = 24,
    description: str | None = None,
) -> Callable:
    """コマンドに承認機能を追加するデコレーター.

    承認権限を持つロール（環境変数 APPROVER_ROLE_NAME で設定、デフォルトは "Administrator"）
    を持つユーザーが実行した場合は即座に実行される。
    それ以外のユーザーが実行した場合は承認リクエストを送信し、
    承認ロールを持つユーザーが承認するまで待機する。

    使用例:
        @command_meta(name="create-channel", description="チャンネル作成")
        @tree.command(name="create-channel")
        @require_approval(timeout_hours=24, description="新しいチャンネルを作成します")
        @app_commands.describe(channel_name="作成するチャンネル名")
        async def create_channel_cmd(ctx: discord.Interaction, channel_name: str):
            await ctx.response.send_message(f"チャンネル {channel_name} を作成しました")

    Args:
        timeout_hours: タイムアウト時間（時間単位）。デフォルトは24時間
        description: 承認リクエストに表示するコマンドの説明（オプション）

    Returns:
        デコレータ関数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
            interaction: discord.Interaction, *args: Any, **kwargs: Any
        ) -> Any:
            # コマンド名を取得
            command_name = getattr(func, "__name__", "unknown")
            if hasattr(func, "name"):
                command_name = func.name

            # Interactionがギルド内でない場合はエラー
            if not interaction.guild or not isinstance(
                interaction.user, discord.Member
            ):
                await interaction.response.send_message(
                    "このコマンドはサーバー内でのみ使用できます。",
                    ephemeral=True,
                )
                return

            # 実行者が承認ロールを持っている場合は即座に実行
            if has_approver_role(interaction.user):
                config = ApprovalConfig.get_instance()
                logger.info(
                    f"Command '{command_name}' executed immediately by {interaction.user} "
                    f"(has '{config.approver_role_name}' role)"
                )
                return await func(interaction, *args, **kwargs)

            # 承認リクエストを送信
            logger.info(
                f"Approval request sent for command '{command_name}' by {interaction.user}"
            )

            # 承認リクエストEmbedを作成
            approval_embed = create_approval_request_embed(
                command_name=command_name,
                requester=interaction.user,
                timeout_hours=timeout_hours,
                description=description,
            )

            # ApprovalViewを作成
            approval_view = ApprovalView(
                command_func=func,
                command_name=command_name,
                original_interaction=interaction,
                args=args,
                kwargs=kwargs,
                timeout_hours=timeout_hours,
            )

            # 承認権限を持つロールを取得
            config = ApprovalConfig.get_instance()
            approver_roles = [
                role
                for role in interaction.guild.roles
                if role.name == config.approver_role_name
            ]

            # 承認権限を持つロールをメンション
            # （複数ある場合は全てメンション）
            mentions = " ".join([f"<@&{role.id}>" for role in approver_roles])
            if not mentions:
                # 承認権限を持つロールがない場合は、ロール名を表示
                mentions = f"**「{config.approver_role_name}」ロールを持つユーザー**"

            # 承認リクエストメッセージを送信
            await interaction.response.send_message(
                content=mentions,
                embed=approval_embed,
                view=approval_view,
                allowed_mentions=discord.AllowedMentions(roles=True),  # ロールメンションを有効化
            )

            # 送信したメッセージをViewに保存（編集用）
            message = await interaction.original_response()
            approval_view.message = message

        return wrapper

    return decorator
