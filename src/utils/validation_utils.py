"""チャンネル実行場所のバリデーション"""

from logging import getLogger

import discord

from .message_utils import send_error_message

logger = getLogger(__name__)


async def validate_channel_restriction(
    ctx: discord.Interaction,
    allowed_channel_name: str,
    must_be_in: bool = True,
) -> bool:
    """コマンドが特定のチャンネルで実行されているかを確認する

    Args:
        ctx: Discord Interaction
        allowed_channel_name: 許可されたチャンネル名
        must_be_in: Trueの場合そのチャンネルでのみ実行可能、
                    Falseの場合そのチャンネル以外で実行可能

    Returns:
        バリデーションが成功した場合True、失敗した場合False
    """
    is_in_channel = ctx.channel.name == allowed_channel_name

    # 早期リターンでシンプルに
    if is_in_channel == must_be_in:
        logger.debug(
            f"Channel validation passed: {ctx.channel.name} "
            f"(required: {allowed_channel_name}, must_be_in: {must_be_in})"
        )
        return True

    # エラーメッセージ用にチャンネルを取得
    guild = ctx.guild
    allowed_channel = discord.utils.get(guild.text_channels, name=allowed_channel_name)

    # チャンネルが見つかった場合はメンション、見つからない場合は名前のみ
    channel_display = (
        allowed_channel.mention if allowed_channel else f"`{allowed_channel_name}`"
    )

    # エラーメッセージ
    if must_be_in:
        await send_error_message(
            ctx,
            f"このコマンドは {channel_display} チャンネルでのみ実行できます。",
            help_text=f"{channel_display} チャンネルに移動してから再度実行してください。",
        )
        logger.info(
            f"Channel restriction failed: {ctx.user} tried to run command in "
            f"#{ctx.channel.name} (required: #{allowed_channel_name})"
        )
    else:
        await send_error_message(
            ctx,
            f"このコマンドは {channel_display} チャンネルでは実行できません。",
            help_text=f"別のチャンネルで実行してください。",
        )
        logger.info(
            f"Channel restriction failed: {ctx.user} tried to run command in "
            f"#{ctx.channel.name} (forbidden: #{allowed_channel_name})"
        )

    return False


async def validate_channel_in_category(
    ctx: discord.Interaction,
    channel: discord.TextChannel,
    category_name: str,
) -> bool:
    """チャンネルが特定のカテゴリーに属しているかを確認する

    Args:
        ctx: Discord Interaction
        channel: 確認対象のチャンネル
        category_name: カテゴリー名

    Returns:
        バリデーションが成功した場合True、失敗した場合False
    """
    if channel.category is None:
        await send_error_message(
            ctx,
            f"チャンネル {channel.mention} はどのカテゴリーにも属していません。",
            help_text=f"`{category_name}` カテゴリー配下のチャンネルでコマンドを実行してください。",
        )
        logger.info(
            f"Category validation failed: {channel.name} has no category "
            f"(required: {category_name})"
        )
        return False

    if channel.category.name != category_name:
        await send_error_message(
            ctx,
            f"チャンネル {channel.mention} は `{category_name}` カテゴリーに属していません。\n"
            f"現在のカテゴリー: `{channel.category.name}`",
            help_text=f"`{category_name}` カテゴリー配下のチャンネルでコマンドを実行するか、"
            f"チャンネル名を指定してください。",
        )
        logger.info(
            f"Category validation failed: {channel.name} is in '{channel.category.name}' "
            f"(required: '{category_name}')"
        )
        return False

    logger.debug(
        f"Category validation passed: {channel.name} is in '{category_name}'"
    )
    return True


async def parse_member_mentions(
    ctx: discord.Interaction,
    members_str: str,
    guild: discord.Guild,
) -> list[discord.Member] | None:
    """メンション文字列からメンバーオブジェクトのリストを抽出する

    Args:
        ctx: Discord Interaction
        members_str: メンション文字列（例: "@user1 @user2"）
        guild: Discordギルド

    Returns:
        メンバーオブジェクトのリスト。エラーの場合はNone
    """
    member_mentions = members_str.strip().split()
    member_objects = []

    for mention in member_mentions:
        # メンションIDを抽出（<@123456789> または <@!123456789> → 123456789）
        member_id = mention.strip("<@!>")
        try:
            member_id_int = int(member_id)
            member = guild.get_member(member_id_int)
            if member:
                member_objects.append(member)
                logger.debug(f"Parsed member mention: {member.name} ({member_id_int})")
            else:
                await send_error_message(
                    ctx,
                    f"メンバー {mention} が見つかりません。",
                    help_text="メンバーがサーバーに存在するか確認してください。",
                )
                logger.warning(f"Member ID {member_id_int} not found in guild")
                return None
        except ValueError:
            await send_error_message(
                ctx,
                f"`{mention}` は有効なメンバーメンションではありません。",
                help_text="メンバーをメンション形式（@ユーザー名）で指定してください。",
            )
            logger.warning(f"Invalid member mention format: {mention}")
            return None

    if not member_objects:
        await send_error_message(
            ctx,
            "メンバーが指定されていません。",
            help_text="メンバーをメンション形式で指定してください。例: @user1 @user2",
        )
        logger.warning("No valid members found in mention string")
        return None

    logger.info(f"Parsed {len(member_objects)} member mentions successfully")
    return member_objects


async def parse_role_mention(
    ctx: discord.Interaction,
    role_str: str,
    guild: discord.Guild,
) -> discord.Role | None:
    """ロール文字列（名前またはメンション）からロールオブジェクトを取得する

    Args:
        ctx: Discord Interaction
        role_str: ロール名またはロールメンション（例: "1-ハッカソン" または "<@&123456789>"）
        guild: Discordギルド

    Returns:
        ロールオブジェクト。見つからない場合はNone
    """
    # ロールメンション形式かチェック（<@&123456789> の形式）
    if role_str.startswith("<@&") and role_str.endswith(">"):
        # メンション形式の場合、IDを抽出
        role_id_str = role_str[3:-1]  # <@&123456789> → 123456789
        try:
            role_id = int(role_id_str)
            role = guild.get_role(role_id)
            if role:
                logger.debug(f"Parsed role mention: {role.name} ({role_id})")
                return role
            else:
                await send_error_message(
                    ctx,
                    f"ロールID `{role_id}` に対応するロールが見つかりません。",
                    help_text="ロールが削除されたか、Botがアクセスできない可能性があります。",
                )
                logger.warning(f"Role ID {role_id} not found in guild")
                return None
        except ValueError:
            await send_error_message(
                ctx,
                f"無効なロールメンション形式です: `{role_str}`",
                help_text="ロールを@メンション形式で指定してください。",
            )
            logger.warning(f"Invalid role mention format: {role_str}")
            return None
    else:
        # メンション形式でない場合は名前として検索
        role = discord.utils.get(guild.roles, name=role_str)
        if not role:
            await send_error_message(
                ctx,
                f"ロール `{role_str}` が見つかりません。",
                help_text="ロール名を確認するか、@メンション形式で指定してください。",
            )
            logger.warning(f"Role '{role_str}' not found in guild")
            return None
        logger.debug(f"Parsed role by name: {role.name} ({role.id})")
        return role


async def validate_role_safety(
    ctx: discord.Interaction,
    role: discord.Role,
) -> bool:
    """ロールが安全に操作可能かを確認する

    以下のロールは操作不可とする:
    - 管理者権限を持つロール
    - Bot専用ロール（managed）
    - @everyoneロール

    Args:
        ctx: Discord Interaction
        role: 確認対象のロール

    Returns:
        安全な場合True、危険な場合False
    """
    # 1. 管理者権限を持つロールはNG
    if role.permissions.administrator:
        await send_error_message(
            ctx,
            f"{role.mention} は管理者権限を持つため、このコマンドでは操作できません。",
            help_text="セキュリティ上の理由から、管理者ロールは操作できません。",
        )
        logger.warning(
            f"Role safety check failed: {role.name} has administrator permission"
        )
        return False

    # 2. Bot専用ロール（managed）はNG
    if role.managed:
        await send_error_message(
            ctx,
            f"{role.mention} はBot専用ロールまたはインテグレーションロールのため、操作できません。",
            help_text="このロールはシステムによって管理されています。",
        )
        logger.warning(f"Role safety check failed: {role.name} is a managed role")
        return False

    # 3. @everyone ロールはNG
    if role.is_default():
        await send_error_message(
            ctx,
            "@everyone ロールは操作できません。",
            help_text="特定のロールを指定してください。",
        )
        logger.warning("Role safety check failed: attempted to use @everyone role")
        return False

    logger.debug(f"Role safety check passed: {role.name}")
    return True
