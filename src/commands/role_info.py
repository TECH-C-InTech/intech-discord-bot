"""ロール情報確認コマンド"""

from logging import getLogger

import discord
from discord import app_commands

from ..utils.command_metadata import command_meta
from ..utils.validation_utils import parse_role_mention, validate_role_safety

logger = getLogger(__name__)


async def show_role_members(
    ctx: discord.Interaction,
    role_name: str,
    visibility: str = "private",
):
    """指定したロールのメンバー一覧を表示するコマンド

    安全なロール（管理者権限なし、Bot管理なし、@everyoneでない）のみ表示可能
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

    # visibilityの値に応じて表示を切り替え（デフォルトは実行者のみ）
    is_private = visibility == "private"

    await ctx.response.send_message(embed=embed, ephemeral=is_private)
    logger.info(
        f"Listed {len(members_with_role)} members for role {role.name} "
        f"(requested by {ctx.user}, visibility: {visibility})"
    )


def setup(tree: app_commands.CommandTree):
    """ロール情報関連のコマンドを登録する"""

    @command_meta(
        category="ロール管理",
        icon="👥",
        short_description="ロールに所属するメンバー一覧を表示",
        restrictions="• 一部ロール以外のみ表示可能",
        examples=[
            "`/show_role_members role_name:@1-event`",
            "`/show_role_members role_name:@1-event visibility:全員に公開`",
        ],
        notes="メンバーが50人を超える場合は自動的に分割して表示されます",
    )
    @tree.command(
        name="show_role_members",
        description="指定したロールのメンバー一覧を表示します",
    )
    @app_commands.describe(
        role_name="対象のロール（@ロール形式で指定。例: @ロール名）",
        visibility="表示範囲を選択",
    )
    @app_commands.choices(
        visibility=[
            app_commands.Choice(name="自分のみ", value="private"),
            app_commands.Choice(name="全員に公開", value="public"),
        ]
    )
    async def show_role_members_cmd(
        ctx: discord.Interaction, role_name: str, visibility: str = "private"
    ):
        await show_role_members(ctx, role_name, visibility)
