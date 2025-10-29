"""ヘルプコマンド"""

from logging import getLogger

import discord
from discord import app_commands

logger = getLogger(__name__)


async def show_help(ctx: discord.Interaction):
    """Botの全コマンドを表示するコマンド"""

    embed = discord.Embed(
        title="🤖 InTech Discord Bot - コマンド一覧",
        description="このBotで利用可能なコマンドの一覧です",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    # イベントチャンネル管理コマンド
    embed.add_field(
        name="📅 イベントチャンネル管理",
        value=(
            "`/create_event_channel <name> [members]`\n"
            "イベントチャンネルとロールを作成。メンバーを指定すると同時にロールに追加\n"
            "※ イベントリクエストチャンネルでのみ実行可能\n\n"
            "`/archive_event_channel [name]`\n"
            "イベントチャンネルをアーカイブに移動\n"
            "※ イベントカテゴリー内のチャンネルでのみ実行可能\n\n"
            "`/restore_event_channel [name]`\n"
            "アーカイブされたチャンネルを復元\n"
            "※ アーカイブカテゴリー内のチャンネルでのみ実行可能"
        ),
        inline=False,
    )

    # ロール管理コマンド
    embed.add_field(
        name="👥 ロール管理",
        value=(
            "`/add_event_role_member <members> [role_name]`\n"
            "イベントチャンネルに紐づくロールにメンバーを追加\n"
            "※ ロール名省略時は実行チャンネルのロールを使用\n\n"
            "`/show_role_members <role_name> [visibility]`\n"
            "指定したロールのメンバー一覧を表示\n"
            "※ `visibility`: 自分のみ（デフォルト）/ 全員に公開\n"
            "※ 安全なロール（管理者権限なし、Bot管理なし、@everyoneでない）のみ表示可能"
        ),
        inline=False,
    )

    # ヘルプ
    embed.add_field(
        name="ℹ️ その他",
        value=("`/help`\nこのヘルプメッセージを表示"),
        inline=False,
    )

    # フッター
    embed.set_footer(
        text="💡 Tip: コマンド入力時に Discord が自動補完してくれます",
        icon_url=ctx.client.user.display_avatar.url,
    )

    await ctx.response.send_message(embed=embed, ephemeral=True)
    logger.info(f"Help command executed by {ctx.user}")


def setup(tree: app_commands.CommandTree):
    """ヘルプコマンドを登録する"""

    @tree.command(
        name="help",
        description="Botの使い方とコマンド一覧を表示します",
    )
    async def help_cmd(ctx: discord.Interaction):
        await show_help(ctx)
