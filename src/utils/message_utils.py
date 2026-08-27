"""Discord メッセージ関連のユーティリティ"""

from logging import getLogger
from typing import Optional

import discord

logger = getLogger(__name__)


def create_success_embed(title: str, description: str, **fields) -> discord.Embed:
    """成功メッセージのEmbedを作成する

    Args:
        title: タイトル（✅アイコンが自動的に追加される）
        description: 説明文
        **fields: フィールド（key=value形式で追加情報を指定）

    Returns:
        discord.Embed: 成功メッセージ用のEmbed

    Example:
        >>> embed = create_success_embed(
        ...     title="チャンネル作成完了",
        ...     description="チャンネルを作成しました",
        ...     チャンネル名="1-ハッカソン",
        ...     メンバー数=5
        ... )
    """
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )

    for name, value in fields.items():
        embed.add_field(name=name, value=str(value), inline=True)

    return embed


def create_error_embed(
    title: str,
    description: str,
    help_text: Optional[str] = None,
) -> discord.Embed:
    """エラーメッセージのEmbedを作成する

    Args:
        title: タイトル（❌アイコンが自動的に追加される）
        description: エラーの説明
        help_text: ヘルプテキスト（任意）

    Returns:
        discord.Embed: エラーメッセージ用のEmbed

    Example:
        >>> embed = create_error_embed(
        ...     title="エラー",
        ...     description="チャンネルが見つかりません",
        ...     help_text="チャンネル名を確認してください"
        ... )
    """
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow(),
    )

    if help_text:
        embed.add_field(name="💡 ヘルプ", value=help_text, inline=False)

    return embed


async def send_error_message(
    ctx: discord.Interaction,
    message: str,
    ephemeral: bool = True,
    help_text: Optional[str] = None,
) -> None:
    """エラーメッセージを送信する

    Args:
        ctx: Discord Interaction
        message: エラーメッセージ
        ephemeral: 自分だけに見えるメッセージにするか（デフォルト: True）
        help_text: ヘルプテキスト（任意）
    """
    if help_text:
        # ヘルプテキストがある場合はEmbedを使用
        embed = create_error_embed(
            title="エラー",
            description=message,
            help_text=help_text,
        )
        try:
            if not ctx.response.is_done():
                await ctx.response.send_message(embed=embed, ephemeral=ephemeral)
            else:
                await ctx.followup.send(embed=embed, ephemeral=ephemeral)
        except discord.NotFound:
            logger.warning(
                "Failed to send error embed because interaction is no longer valid: %s",
                message,
            )
            return
    else:
        # シンプルなエラーメッセージ
        try:
            if not ctx.response.is_done():
                await ctx.response.send_message(f"❌ {message}", ephemeral=ephemeral)
            else:
                await ctx.followup.send(f"❌ {message}", ephemeral=ephemeral)
        except discord.NotFound:
            logger.warning(
                "Failed to send error message because interaction is no longer valid: %s",
                message,
            )
            return

    logger.info(f"Error message sent to {ctx.user}: {message}")


async def handle_command_error(
    ctx: discord.Interaction,
    error: Exception,
    action: str,
    help_text: Optional[str] = None,
    custom_help_texts: Optional[dict[type[Exception], str]] = None,
) -> None:
    """コマンド実行時のエラーをハンドリングする

    一般的なDiscordエラーを適切にハンドリングし、ユーザーにわかりやすいメッセージを表示する。

    Args:
        ctx: Discord Interaction
        error: 発生したエラー
        action: 実行していたアクション（例: "チャンネルの作成"）
        help_text: 全エラー共通のカスタムヘルプテキスト（任意）
        custom_help_texts: エラータイプごとのカスタムヘルプテキスト（任意）
            例: {discord.Forbidden: "カスタムメッセージ"}
    """
    logger.error(f"Error during {action}: {error}", exc_info=True)

    default_help_texts = {
        discord.Forbidden: "サーバー管理者にBotの権限設定を確認してください。",
        discord.NotFound: "対象が削除されたか、アクセス権限がない可能性があります。",
        discord.HTTPException: "時間をおいて再度お試しください。",
    }

    error_messages = {
        discord.Forbidden: f"Botに{action}する権限がありません。",
        discord.NotFound: f"{action}対象が見つかりませんでした。",
        discord.HTTPException: f"{action}中にDiscord APIエラーが発生しました。",
    }

    for error_type, message in error_messages.items():
        if isinstance(error, error_type):
            # 優先順位: custom_help_texts > help_text > default_help_texts
            final_help_text = (
                (custom_help_texts or {}).get(error_type)
                or help_text
                or default_help_texts[error_type]
            )
            await send_error_message(ctx, message, help_text=final_help_text)
            return

    # その他の予期しないエラー
    await send_error_message(
        ctx,
        f"{action}中にエラーが発生しました: {type(error).__name__}",
        help_text=help_text or "管理者に連絡してください。",
    )
