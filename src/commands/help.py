"""ヘルプコマンド"""

from logging import getLogger

import discord
from discord import app_commands

logger = getLogger(__name__)


async def show_help(ctx: discord.Interaction):
    """Botの全コマンドを簡潔に表示するコマンド"""

    embed = discord.Embed(
        title="🤖 InTech Discord Bot",
        description="利用可能なコマンド一覧",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    # イベントチャンネル管理コマンド
    embed.add_field(
        name="📅 イベントチャンネル管理",
        value=(
            "`/create_event_channel` - イベントチャンネル作成\n"
            "`/archive_event_channel` - イベントをアーカイブ\n"
            "`/restore_event_channel` - アーカイブから復元"
        ),
        inline=False,
    )

    # ロール管理コマンド
    embed.add_field(
        name="👥 ロール管理",
        value=(
            "`/add_event_role_member` - イベントロールにメンバー追加\n"
            "`/show_role_members` - ロールメンバー一覧表示"
        ),
        inline=False,
    )

    # ヘルプ・ドキュメント
    embed.add_field(
        name="ℹ️ ヘルプ",
        value=(
            "`/help` - このメッセージを表示\n"
            "`/docs [command]` - コマンドの詳細を表示"
        ),
        inline=False,
    )

    # フッター
    embed.set_footer(
        text="💡 詳細は /docs コマンドで確認できます",
        icon_url=ctx.client.user.display_avatar.url,
    )

    await ctx.response.send_message(embed=embed, ephemeral=True)
    logger.info(f"Help command executed by {ctx.user}")


# コマンドのドキュメント情報
COMMAND_DOCS = {
    "create_event_channel": {
        "title": "📅 /create_event_channel",
        "description": "イベントチャンネルとロールを作成します",
        "usage": "`/create_event_channel <name> [members]`",
        "parameters": (
            "**name**: イベント名（必須）\n"
            "**members**: 追加するメンバー（任意、メンション形式で複数指定可能）"
        ),
        "restrictions": "• イベントリクエストチャンネルでのみ実行可能",
        "examples": (
            "`/create_event_channel name:ハッカソン`\n"
            "`/create_event_channel name:勉強会 members:@user1 @user2`"
        ),
    },
    "archive_event_channel": {
        "title": "📦 /archive_event_channel",
        "description": "イベントチャンネルをアーカイブに移動します",
        "usage": "`/archive_event_channel [name]`",
        "parameters": "**name**: チャンネル名（省略時は実行チャンネル）",
        "restrictions": "• イベントカテゴリー内のチャンネルでのみ実行可能",
        "examples": (
            "`/archive_event_channel` (実行チャンネルをアーカイブ)\n"
            "`/archive_event_channel name:1-ハッカソン`"
        ),
    },
    "restore_event_channel": {
        "title": "♻️ /restore_event_channel",
        "description": "アーカイブされたチャンネルを復元します",
        "usage": "`/restore_event_channel [name]`",
        "parameters": "**name**: チャンネル名（省略時は実行チャンネル）",
        "restrictions": "• アーカイブカテゴリー内のチャンネルでのみ実行可能",
        "examples": (
            "`/restore_event_channel` (実行チャンネルを復元)\n"
            "`/restore_event_channel name:1-ハッカソン`"
        ),
    },
    "add_event_role_member": {
        "title": "� /add_event_role_member",
        "description": "イベントチャンネルに紐づくロールにメンバーを追加します",
        "usage": "`/add_event_role_member <members> [role_name]`",
        "parameters": (
            "**members**: 追加するメンバー（必須、メンション形式で複数指定可能）\n"
            "**role_name**: 対象のロール（任意、@ロール形式で指定。省略時は実行チャンネルのロール）"
        ),
        "restrictions": "• 安全なロール（管理者権限なし、Bot管理なし、@everyoneでない）のみ対象",
        "examples": (
            "`/add_event_role_member members:@user1 @user2`\n"
            "`/add_event_role_member members:@user1 role_name:@1-event`"
        ),
    },
    "show_role_members": {
        "title": "👥 /show_role_members",
        "description": "指定したロールのメンバー一覧を表示します",
        "usage": "`/show_role_members <role_name> [visibility]`",
        "parameters": (
            "**role_name**: 対象のロール（必須、@ロール形式で指定）\n"
            "**visibility**: 表示範囲（任意）\n"
            "  • `自分のみ` - 実行者のみに表示（デフォルト）\n"
            "  • `全員に公開` - チャンネル内全員に表示"
        ),
        "restrictions": "• 安全なロール（管理者権限なし、Bot管理なし、@everyoneでない）のみ表示可能",
        "examples": (
            "`/show_role_members role_name:@1-event`\n"
            "`/show_role_members role_name:@1-event visibility:全員に公開`"
        ),
    },
}


async def show_docs(ctx: discord.Interaction, command: str = None):
    """コマンドの詳細ドキュメントを表示する"""

    if command is None:
        # コマンドが指定されていない場合、一覧を表示
        embed = discord.Embed(
            title="📚 コマンドドキュメント",
            description="詳細を確認したいコマンドを選択してください",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )

        available_commands = "\n".join(
            [f"• `/docs command:{cmd}`" for cmd in sorted(COMMAND_DOCS.keys())]
        )
        embed.add_field(
            name="利用可能なコマンド",
            value=available_commands,
            inline=False,
        )

        embed.set_footer(text="例: /docs command:create_event_channel")

    else:
        # 指定されたコマンドの詳細を表示
        if command not in COMMAND_DOCS:
            embed = discord.Embed(
                title="❌ エラー",
                description=f"コマンド `{command}` のドキュメントが見つかりません。",
                color=discord.Color.red(),
            )
            embed.add_field(
                name="利用可能なコマンド",
                value=", ".join([f"`{cmd}`" for cmd in sorted(COMMAND_DOCS.keys())]),
                inline=False,
            )
        else:
            doc = COMMAND_DOCS[command]
            embed = discord.Embed(
                title=doc["title"],
                description=doc["description"],
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(name="📝 使い方", value=doc["usage"], inline=False)
            embed.add_field(name="⚙️ パラメータ", value=doc["parameters"], inline=False)
            embed.add_field(name="🚫 実行制限", value=doc["restrictions"], inline=False)
            embed.add_field(name="💡 例", value=doc["examples"], inline=False)

    await ctx.response.send_message(embed=embed, ephemeral=True)
    logger.info(
        f"Docs command executed by {ctx.user}" + (f" for {command}" if command else "")
    )


def setup(tree: app_commands.CommandTree):
    """ヘルプコマンドを登録する"""

    @tree.command(
        name="help",
        description="Botのコマンド一覧を表示します",
    )
    async def help_cmd(ctx: discord.Interaction):
        await show_help(ctx)

    @tree.command(
        name="docs",
        description="コマンドの詳細ドキュメントを表示します",
    )
    @app_commands.describe(command="詳細を確認したいコマンド名（省略時は一覧を表示）")
    @app_commands.choices(
        command=[
            app_commands.Choice(name="create_event_channel", value="create_event_channel"),
            app_commands.Choice(name="archive_event_channel", value="archive_event_channel"),
            app_commands.Choice(name="restore_event_channel", value="restore_event_channel"),
            app_commands.Choice(name="add_event_role_member", value="add_event_role_member"),
            app_commands.Choice(name="show_role_members", value="show_role_members"),
        ]
    )
    async def docs_cmd(ctx: discord.Interaction, command: str = None):
        await show_docs(ctx, command)

