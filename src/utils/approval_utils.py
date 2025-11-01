"""承認ミドルウェア用のユーティリティ関数."""

from datetime import datetime, timezone

import discord

from src.utils.approval_config import ApprovalConfig


def create_approval_request_embed(
    command_name: str,
    requester: discord.User | discord.Member,
    timeout_hours: int,
    description: str | None = None,
) -> discord.Embed:
    """承認リクエスト用のEmbedを作成する.

    Args:
        command_name: コマンド名
        requester: リクエストしたユーザー
        timeout_hours: タイムアウト時間（時間単位）
        description: コマンドの説明（オプション）

    Returns:
        承認リクエスト用のEmbed
    """
    embed = discord.Embed(
        title="📋 承認リクエスト",
        description=f"{requester.mention} がコマンド `{command_name}` の実行を要求しています。",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc),
    )

    if description:
        embed.add_field(name="実行内容", value=description, inline=False)

    embed.add_field(name="リクエスト者", value=requester.mention, inline=True)
    embed.add_field(name="タイムアウト", value=f"{timeout_hours}時間", inline=True)

    config = ApprovalConfig.get_instance()
    embed.set_footer(text=f"「{config.approver_role_name}」ロールを持つユーザーが承認できます")

    return embed


def create_request_details_embed(
    command_name: str,
    args: tuple,
    kwargs: dict,
    description: str | None = None,
) -> discord.Embed:
    """リクエスト詳細Embed を作成する（スレッド内に投稿）.

    Args:
        command_name: コマンド名
        args: コマンドの位置引数
        kwargs: コマンドのキーワード引数
        description: コマンドの説明（オプション）

    Returns:
        リクエスト詳細用のEmbed
    """
    embed = discord.Embed(
        title="📝 リクエスト詳細",
        description=f"コマンド: `{command_name}`",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc),
    )

    if description:
        embed.add_field(name="説明", value=description, inline=False)

    # 引数を整形して表示
    if kwargs:
        args_text = []
        for key, value in kwargs.items():
            # 値が長い場合は省略
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            args_text.append(f"• **{key}**: {value_str}")

        if args_text:
            embed.add_field(
                name="引数",
                value="\n".join(args_text),
                inline=False,
            )

    return embed


def create_approval_result_embed(
    command_name: str,
    approver: discord.User | discord.Member,
    requester: discord.User | discord.Member,
) -> discord.Embed:
    """承認成功用のEmbedを作成する.

    Args:
        command_name: コマンド名
        approver: 承認したユーザー
        requester: リクエストしたユーザー

    Returns:
        承認成功用のEmbed
    """
    embed = discord.Embed(
        title="✅ 承認されました",
        description=f"コマンド `{command_name}` が承認されました。",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )

    embed.add_field(name="リクエスト者", value=requester.mention, inline=True)
    embed.add_field(name="承認者", value=approver.mention, inline=True)

    return embed


def create_rejection_result_embed(
    command_name: str,
    rejector: discord.User | discord.Member,
    requester: discord.User | discord.Member,
) -> discord.Embed:
    """拒否用のEmbedを作成する.

    Args:
        command_name: コマンド名
        rejector: 拒否したユーザー
        requester: リクエストしたユーザー

    Returns:
        拒否用のEmbed
    """
    embed = discord.Embed(
        title="❌ 拒否されました",
        description=f"コマンド `{command_name}` は拒否されました。",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc),
    )

    embed.add_field(name="リクエスト者", value=requester.mention, inline=True)
    embed.add_field(name="拒否者", value=rejector.mention, inline=True)

    return embed


def create_timeout_result_embed(command_name: str, timeout_hours: int) -> discord.Embed:
    """タイムアウト用のEmbedを作成する.

    Args:
        command_name: コマンド名
        timeout_hours: タイムアウト時間（時間単位）

    Returns:
        タイムアウト用のEmbed
    """
    embed = discord.Embed(
        title="⏱️ タイムアウト",
        description=f"コマンド `{command_name}` は\n"
        f"{timeout_hours}時間以内に承認されなかったため、自動的に拒否されました。",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc),
    )

    return embed


def has_approver_role(member: discord.Member) -> bool:
    """ユーザーが承認権限を持つロールを持っているかチェックする.

    承認権限を持つロール名は環境変数 APPROVER_ROLE_NAME で設定する。
    デフォルトは "Administrator"。

    Args:
        member: チェックするメンバー

    Returns:
        承認権限を持つロールを持っている場合はTrue
    """
    config = ApprovalConfig.get_instance()
    return any(role.name == config.approver_role_name for role in member.roles)
