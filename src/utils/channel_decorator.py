"""チャンネル制限デコレーター."""

from collections.abc import Callable
from functools import wraps
from logging import getLogger
from typing import Any

import discord

from src.utils.event_config import EventChannelConfig
from src.utils.validation_utils import validate_channel_restriction

logger = getLogger(__name__)


def require_channel(
    channel_name: str | None = None,
    channel_name_from_config: str | None = None,
    must_be_in: bool = True,
) -> Callable:
    """コマンドにチャンネル制限を追加するデコレーター.

    指定されたチャンネルでのみ（または指定されたチャンネル以外で）
    コマンドを実行できるように制限する。

    このデコレーターは @require_approval より上位に配置する必要がある。
    これにより、承認リクエスト送信前にチャンネル制限をチェックできる。

    使用例:
        # チャンネル名を直接指定
        @command_meta(name="create-channel", description="チャンネル作成")
        @tree.command(name="create-channel")
        @require_channel(channel_name="管理チャンネル", must_be_in=True)
        @require_approval(timeout_hours=24)
        @app_commands.describe(channel_name="作成するチャンネル名")
        async def create_channel_cmd(ctx: discord.Interaction, channel_name: str):
            await ctx.response.send_message(f"チャンネル {channel_name} を作成しました")

        # 環境変数から動的に取得
        @command_meta(name="archive", description="アーカイブ")
        @tree.command(name="archive")
        @require_channel(channel_name_from_config="event_request_channel_name", must_be_in=False)
        @app_commands.describe(channel="アーカイブするチャンネル")
        async def archive_cmd(ctx: discord.Interaction, channel: discord.TextChannel):
            await ctx.response.send_message(f"チャンネル {channel.name} をアーカイブしました")

    Args:
        channel_name: チャンネル名を直接指定（channel_name_from_config と排他）
        channel_name_from_config: EventChannelConfig の属性名を指定して動的取得
                                  （channel_name と排他）
        must_be_in: チャンネル制限の方向
                    - True: 指定チャンネルでのみ実行可能
                    - False: 指定チャンネル以外で実行可能

    Returns:
        デコレータ関数

    Raises:
        ValueError: channel_name と channel_name_from_config の両方が未指定、
                   または両方が指定されている場合
    """
    # パラメータの検証
    if channel_name is None and channel_name_from_config is None:
        raise ValueError(
            "require_channel: channel_name または channel_name_from_config "
            "のいずれかを指定してください"
        )

    if channel_name is not None and channel_name_from_config is not None:
        raise ValueError(
            "require_channel: channel_name と channel_name_from_config を同時に指定できません"
        )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args: Any, **kwargs: Any) -> Any:
            # コマンド名を取得
            command_name = getattr(func, "__name__", "unknown")
            if hasattr(func, "name"):
                command_name = func.name

            # チャンネル名を取得
            target_channel_name = channel_name

            # 環境変数から動的に取得する場合
            if channel_name_from_config:
                config = await EventChannelConfig.load(interaction)
                if not config:
                    # 設定の読み込みに失敗した場合は早期リターン
                    # （EventChannelConfig.load 内でエラーメッセージが送信される）
                    logger.error(f"Failed to load EventChannelConfig for command '{command_name}'")
                    return

                # 属性が存在するかチェック
                if not hasattr(config, channel_name_from_config):
                    logger.error(
                        f"EventChannelConfig has no attribute '{channel_name_from_config}' "
                        f"for command '{command_name}'"
                    )
                    if interaction.response.is_done():
                        await interaction.followup.send(
                            f"設定エラー: 環境変数 `{channel_name_from_config}` が見つかりません。",
                            ephemeral=True,
                        )
                    else:
                        await interaction.response.send_message(
                            f"設定エラー: 環境変数 `{channel_name_from_config}` が見つかりません。",
                            ephemeral=True,
                        )
                    return

                target_channel_name = getattr(config, channel_name_from_config)

            # target_channel_name が None でないことを保証
            if target_channel_name is None:
                logger.error(f"Channel name is None for command '{command_name}'")
                if interaction.response.is_done():
                    await interaction.followup.send(
                        "設定エラー: チャンネル名が取得できませんでした。",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "設定エラー: チャンネル名が取得できませんでした。",
                        ephemeral=True,
                    )
                return

            # チャンネル制限をチェック
            if not await validate_channel_restriction(interaction, target_channel_name, must_be_in):
                # バリデーション失敗（エラーメッセージはvalidate_channel_restriction内で送信される）
                logger.info(
                    f"Command '{command_name}' blocked by channel restriction: "
                    f"channel='{target_channel_name}', must_be_in={must_be_in}, "
                    f"user={interaction.user}"
                )
                return

            # バリデーション成功 → 元の関数を実行
            logger.debug(
                f"Channel restriction passed for command '{command_name}': "
                f"channel='{target_channel_name}', must_be_in={must_be_in}, "
                f"user={interaction.user}"
            )
            return await func(interaction, *args, **kwargs)

        return wrapper

    return decorator
