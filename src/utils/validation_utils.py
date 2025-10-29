"""チャンネル実行場所のバリデーション"""

import discord

from .message_utils import send_error_message


async def validate_channel_restriction(
    ctx: discord.Interaction,
    allowed_channel_name: str,
    must_be_in: bool = True,
) -> bool:
    """
    コマンドが特定のチャンネルで実行されているかを確認する

    Args:
        ctx: Discord Interaction
        allowed_channel_name: 許可されたチャンネル名
        must_be_in: Trueの場合そのチャンネルでのみ実行可能、Falseの場合そのチャンネル以外で実行可能

    Returns:
        バリデーションが成功した場合True
    """
    is_in_channel = ctx.channel.name == allowed_channel_name

    # 早期リターンでシンプルに
    if is_in_channel == must_be_in:
        return True

    # エラーメッセージ
    if must_be_in:
        await send_error_message(
            ctx,
            f"このコマンドは '{allowed_channel_name}' チャンネルでのみ実行できます。",
        )
    else:
        await send_error_message(
            ctx,
            f"このコマンドは '{allowed_channel_name}' チャンネルでは実行できません。",
        )

    return False


async def validate_channel_in_category(
    ctx: discord.Interaction,
    channel: discord.TextChannel,
    category_name: str,
) -> bool:
    """
    チャンネルが特定のカテゴリーに属しているかを確認する

    Args:
        ctx: Discord Interaction
        channel: 確認対象のチャンネル
        category_name: カテゴリー名

    Returns:
        バリデーションが成功した場合True
    """
    if channel.category is None or channel.category.name != category_name:
        await send_error_message(
            ctx,
            f"チャンネル '{channel.name}' はイベントカテゴリー '{category_name}' に属していません。\n"
            f"{category_name}配下のアーカイブしたいチャンネルでコマンドを実行するか、チャンネル名を指定してください。",
        )
        return False
    return True
