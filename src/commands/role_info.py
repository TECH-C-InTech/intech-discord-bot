"""ロール情報確認コマンド"""

from logging import getLogger

import discord
from discord import app_commands

from ..utils.validation_utils import parse_role_mention, validate_role_safety

logger = getLogger(__name__)


async def show_role_members(
    ctx: discord.Interaction,
    role_name: str,
):
    """指定したロールのメンバー一覧を表示するコマンド

    安全なロール（管理者権限なし、Bot管理なし、@everyoneでない）のみ表示可能
    実行者にのみ表示される（ephemeral）
    """

    guild = ctx.guild

    # ロールをパース
    role = await parse_role_mention(ctx, role_name, guild)
    if not role:
        return

    # ロールの安全性チェック
    if not await validate_role_safety(ctx, role):
        return

    # ロールを持っているメンバーを取得
    members_with_role = [member for member in guild.members if role in member.roles]

    # Embedを作成
    embed = discord.Embed(
        title=f"🎭 {role.name} のメンバー一覧",
        color=role.color
        if role.color != discord.Color.default()
        else discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    embed.add_field(
        name="📊 メンバー数",
        value=f"{len(members_with_role)}人",
        inline=False,
    )

    if members_with_role:
        # メンバーを50人ずつに分割（Embedのフィールド制限対策）
        chunk_size = 50
        for i in range(0, len(members_with_role), chunk_size):
            chunk = members_with_role[i : i + chunk_size]
            member_list = "\n".join(
                [f"• {member.mention} ({member.name})" for member in chunk]
            )

            field_name = (
                "👥 メンバー" if i == 0 else f"👥 メンバー (続き {i // chunk_size + 1})"
            )
            embed.add_field(
                name=field_name,
                value=member_list,
                inline=False,
            )
    else:
        embed.add_field(
            name="👥 メンバー",
            value="このロールにはまだメンバーがいません",
            inline=False,
        )

    # ephemeral=Trueで実行者にのみ表示
    await ctx.response.send_message(embed=embed, ephemeral=True)
    logger.info(
        f"Listed {len(members_with_role)} members for role {role.name} "
        f"(requested by {ctx.user})"
    )


def setup(tree: app_commands.CommandTree):
    """ロール情報関連のコマンドを登録する"""

    @tree.command(
        name="show_role_members",
        description="指定したロールのメンバー一覧を表示します（実行者にのみ表示）",
    )
    @app_commands.describe(
        role_name="対象のロール（@ロール形式で指定。例: @ロール名）",
    )
    async def show_role_members_cmd(ctx: discord.Interaction, role_name: str):
        await show_role_members(ctx, role_name)
