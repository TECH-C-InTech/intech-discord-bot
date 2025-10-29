"""Discord メッセージ関連のユーティリティ"""

import discord


def create_success_embed(title: str, description: str, **fields) -> discord.Embed:
    """
    成功メッセージのEmbedを作成する

    Args:
        title: タイトル
        description: 説明
        **fields: フィールド (key=value形式)

    Returns:
        discord.Embed
    """
    embed = discord.Embed(
        title=f"✅ {title}", description=description, color=discord.Color.green()
    )
    for name, value in fields.items():
        embed.add_field(name=name, value=str(value), inline=True)
    return embed


async def send_error_message(
    ctx: discord.Interaction, message: str, ephemeral: bool = True
) -> None:
    """
    エラーメッセージを送信する

    Args:
        ctx: Discord Interaction
        message: エラーメッセージ
        ephemeral: 自分だけに見えるメッセージにするか
    """
    await ctx.response.send_message(f"❌ {message}", ephemeral=ephemeral)


async def handle_command_error(
    ctx: discord.Interaction, error: Exception, action: str
) -> None:
    """
    コマンド実行時のエラーをハンドリングする

    Args:
        ctx: Discord Interaction
        error: 発生したエラー
        action: 実行していたアクション（例: "チャンネルの作成"）
    """
    if isinstance(error, discord.Forbidden):
        await send_error_message(ctx, f"Botに{action}する権限がありません。")
    else:
        await send_error_message(ctx, f"{action}中にエラーが発生しました: {str(error)}")
