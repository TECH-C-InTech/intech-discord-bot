"""承認/拒否ボタンを持つViewクラス."""

from collections.abc import Callable
from logging import getLogger
from typing import Any

import discord
from discord.errors import InteractionResponded

from src.utils.approval_config import ApprovalConfig
from src.utils.approval_utils import (
    create_approval_result_embed,
    create_rejection_result_embed,
    create_timeout_result_embed,
    has_approver_role,
)
from src.utils.message_utils import send_error_message

logger = getLogger(__name__)


class ThreadBoundResponse:
    """Wrap interaction response so messages are redirected to the thread."""

    def __init__(
        self,
        original_response: discord.InteractionResponse,
        thread: discord.Thread,
    ) -> None:
        self._original_response = original_response
        self._thread = thread

    async def send_message(self, *args: Any, **kwargs: Any) -> discord.InteractionResponse | None:
        # Threads do not support ephemeral messages; drop the flag quietly.
        kwargs.pop("ephemeral", None)
        await self._thread.send(*args, **kwargs)
        return None

    async def defer(self, *args: Any, **kwargs: Any) -> None:
        # The original interaction has already been responded to; defer is best-effort.
        try:
            await self._original_response.defer(*args, **kwargs)
        except (InteractionResponded, discord.HTTPException):
            pass

    def is_done(self) -> bool:
        return True

    async def edit_message(self, *args: Any, **kwargs: Any) -> Any:
        return await self._original_response.edit_message(*args, **kwargs)


class ThreadBoundFollowup:
    """Redirect follow-up messages to the approval thread."""

    def __init__(self, thread: discord.Thread) -> None:
        self._thread = thread

    async def send(self, *args: Any, **kwargs: Any) -> discord.Message:
        kwargs.pop("ephemeral", None)
        return await self._thread.send(*args, **kwargs)


class ThreadBoundInteraction:
    """Interaction wrapper that routes output to the approval thread."""

    def __init__(
        self,
        original_interaction: discord.Interaction,
        thread: discord.Thread,
    ) -> None:
        self._original_interaction = original_interaction
        self._thread = thread
        self.response = ThreadBoundResponse(original_interaction.response, thread)
        self.followup = ThreadBoundFollowup(thread)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._original_interaction, item)

    @property
    def channel(self) -> discord.abc.MessageableChannel | None:
        return self._original_interaction.channel

    @property
    def approval_thread(self) -> discord.Thread:
        return self._thread


class ApprovalView(discord.ui.View):
    """承認/拒否ボタンを持つViewクラス.

    Attributes:
        command_func: 承認後に実行するコマンド関数
        command_name: コマンド名
        original_interaction: 元のInteraction
        args: コマンド関数の位置引数
        kwargs: コマンド関数のキーワード引数
        timeout_hours: タイムアウト時間（時間単位）
        message: 承認リクエストメッセージ（後から設定）
        thread: 承認フロー用のスレッド（後から設定）
    """

    def __init__(
        self,
        command_func: Callable,
        command_name: str,
        original_interaction: discord.Interaction,
        args: tuple,
        kwargs: dict[str, Any],
        timeout_hours: int = 24,
    ) -> None:
        """初期化.

        Args:
            command_func: 承認後に実行するコマンド関数
            command_name: コマンド名
            original_interaction: 元のInteraction
            args: コマンド関数の位置引数
            kwargs: コマンド関数のキーワード引数
            timeout_hours: タイムアウト時間（時間単位）
        """
        # タイムアウトを秒単位に変換
        super().__init__(timeout=timeout_hours * 3600)

        self.command_func = command_func
        self.command_name = command_name
        self.original_interaction = original_interaction
        self.args = args
        self.kwargs = kwargs
        self.timeout_hours = timeout_hours
        self.message: discord.Message | None = None
        self.thread: discord.Thread | None = None

    @discord.ui.button(label="承認", style=discord.ButtonStyle.green, emoji="✅")
    async def approve_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """承認ボタンのコールバック.

        Args:
            interaction: ボタンクリック時のInteraction
            button: クリックされたボタン
        """
        # 権限チェック
        if not isinstance(interaction.user, discord.Member):
            await send_error_message(
                interaction,
                "このコマンドはサーバー内でのみ使用できます。",
                ephemeral=True,
            )
            return

        if not has_approver_role(interaction.user):
            config = ApprovalConfig.get_instance()
            await send_error_message(
                interaction,
                f"承認権限がありません。「{config.approver_role_name}」ロールが必要です。",
                ephemeral=True,
            )
            logger.warning(f"User {interaction.user} attempted to approve without permission")
            return

        # 応答時間を延長（コマンド実行に時間がかかる可能性があるため）
        await interaction.response.defer()

        logger.info(
            f"Command '{self.command_name}' approved by {interaction.user} "
            f"(requested by {self.original_interaction.user})"
        )

        # ボタンを無効化
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        # 承認メッセージを編集
        approval_embed = create_approval_result_embed(
            self.command_name, interaction.user, self.original_interaction.user
        )

        if self.message:
            try:
                await self.message.edit(embed=approval_embed, view=self)
            except discord.HTTPException as e:
                logger.error(f"Failed to edit approval message: {e}")

        # スレッド内に承認通知を投稿
        if self.thread:
            try:
                notification_embed = create_approval_result_embed(
                    self.command_name, interaction.user, self.original_interaction.user
                )
                await self.thread.send(embed=notification_embed)
            except discord.HTTPException as e:
                logger.error(f"Failed to send approval notification to thread: {e}")

        # 元のコマンドを実行（新しいInteractionコンテキストで）
        interaction_for_command = (
            ThreadBoundInteraction(self.original_interaction, self.thread)
            if self.thread
            else self.original_interaction
        )

        try:
            # 元のコマンドにスレッドへ束縛されたInteractionを渡して実行
            await self.command_func(interaction_for_command, *self.args, **self.kwargs)
        except Exception as e:
            logger.error(
                f"Error executing approved command '{self.command_name}': {e}",
                exc_info=True,
            )
            await send_error_message(
                interaction,
                f"コマンドの実行中にエラーが発生しました: {e}",
                ephemeral=False,
            )

        # Viewを停止
        self.stop()

    @discord.ui.button(label="拒否", style=discord.ButtonStyle.red, emoji="❌")
    async def reject_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """拒否ボタンのコールバック.

        Args:
            interaction: ボタンクリック時のInteraction
            button: クリックされたボタン
        """
        # 権限チェック
        if not isinstance(interaction.user, discord.Member):
            await send_error_message(
                interaction,
                "このコマンドはサーバー内でのみ使用できます。",
                ephemeral=True,
            )
            return

        if not has_approver_role(interaction.user):
            config = ApprovalConfig.get_instance()
            await send_error_message(
                interaction,
                f"拒否権限がありません。「{config.approver_role_name}」ロールが必要です。",
                ephemeral=True,
            )
            logger.warning(f"User {interaction.user} attempted to reject without permission")
            return

        await interaction.response.defer()

        logger.info(
            f"Command '{self.command_name}' rejected by {interaction.user} "
            f"(requested by {self.original_interaction.user})"
        )

        # ボタンを無効化
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        # 拒否メッセージを編集
        rejection_embed = create_rejection_result_embed(
            self.command_name, interaction.user, self.original_interaction.user
        )

        if self.message:
            try:
                await self.message.edit(embed=rejection_embed, view=self)
            except discord.HTTPException as e:
                logger.error(f"Failed to edit rejection message: {e}")

        # スレッド内に拒否通知を投稿
        if self.thread:
            try:
                notification_embed = create_rejection_result_embed(
                    self.command_name, interaction.user, self.original_interaction.user
                )
                await self.thread.send(embed=notification_embed)
            except discord.HTTPException as e:
                logger.error(f"Failed to send rejection notification to thread: {e}")

        # リクエスト者に通知（スレッド内に投稿）
        if self.thread:
            try:
                await self.thread.send(
                    f"{self.original_interaction.user.mention} コマンド `{self.command_name}`"
                    " は拒否されました。"
                )
            except discord.HTTPException as e:
                logger.error(f"Failed to send rejection notification: {e}")

        # Viewを停止
        self.stop()

    async def on_timeout(self) -> None:
        """タイムアウト時の処理."""
        logger.warning(
            f"Approval request for command '{self.command_name}' timed out "
            f"(requested by {self.original_interaction.user})"
        )

        # ボタンを無効化
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        # タイムアウトメッセージを編集
        timeout_embed = create_timeout_result_embed(self.command_name, self.timeout_hours)

        if self.message:
            try:
                await self.message.edit(embed=timeout_embed, view=self)
            except discord.HTTPException as e:
                logger.error(f"Failed to edit timeout message: {e}")
