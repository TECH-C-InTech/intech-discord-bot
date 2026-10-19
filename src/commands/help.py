"""ヘルプコマンド"""

from logging import getLogger

import discord
from discord import app_commands

from ..utils.command_metadata import (
    command_meta,
    get_all_metadata,
    get_command_metadata,
)

logger = getLogger(__name__)


# ==================== コマンド実装関数 ====================


async def help_impl(ctx: discord.Interaction):
    """Botの全コマンドを簡潔に表示する"""
    embed = discord.Embed(
        title="🤖 InTech Discord Bot",
        description="利用可能なコマンド一覧",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    # メタデータを取得してカテゴリー別にグループ化
    all_metadata = get_all_metadata()
    categories: dict[tuple[str, str], list[tuple[str, str]]] = {}

    for cmd_name, metadata in all_metadata.items():
        category_key = (metadata.category, metadata.icon)
        if category_key not in categories:
            categories[category_key] = []
        # short_description が None の場合は空文字列を使用
        short_desc = metadata.short_description or ""
        categories[category_key].append((cmd_name, short_desc))

    # カテゴリー別に表示
    for (category_name, icon), commands in sorted(categories.items()):
        command_list = []
        for cmd_name, short_desc in sorted(commands):
            if short_desc:
                command_list.append(f"`/{cmd_name}` - {short_desc}")
            else:
                command_list.append(f"`/{cmd_name}`")

        embed.add_field(
            name=f"{icon} {category_name}",
            value="\n".join(command_list),
            inline=False,
        )

    # フッター
    if ctx.client.user:
        embed.set_footer(
            text="💡 詳細は /docs コマンドで確認できます",
            icon_url=ctx.client.user.display_avatar.url,
        )
    else:
        embed.set_footer(text="💡 詳細は /docs コマンドで確認できます")

    if ctx.response.is_done():
        await ctx.followup.send(embed=embed, ephemeral=True)
    else:
        await ctx.response.send_message(embed=embed, ephemeral=True)
    logger.info(f"Help command executed by {ctx.user}")


async def docs_impl(
    tree: discord.app_commands.CommandTree,
    ctx: discord.Interaction,
    command: str | None = None,
):
    """コマンドの詳細ドキュメントを表示する

    Args:
        tree: コマンドツリー
        ctx: Discord Interaction
        command: コマンド名（省略時は一覧を表示）
    """
    all_commands = {cmd.name: cmd for cmd in tree.get_commands()}

    if command is None:
        # コマンドが指定されていない場合、一覧を表示
        embed = discord.Embed(
            title="📚 コマンドドキュメント",
            description="詳細を確認したいコマンドを選択してください",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )

        # メタデータが登録されているコマンド一覧
        metadata_commands = list(get_all_metadata().keys())
        if metadata_commands:
            available_commands = "\n".join(
                [f"• `/docs command:{cmd}`" for cmd in sorted(metadata_commands)]
            )
            embed.add_field(
                name="利用可能なコマンド",
                value=available_commands,
                inline=False,
            )
        else:
            embed.add_field(
                name="利用可能なコマンド",
                value="コマンドのメタデータが登録されていません",
                inline=False,
            )

        embed.set_footer(text="例: /docs command:create_channel")

    else:
        # 指定されたコマンドの詳細を表示
        metadata = get_command_metadata(command)
        cmd_obj = all_commands.get(command)

        if not metadata or not cmd_obj:
            embed = discord.Embed(
                title="❌ エラー",
                description=f"コマンド `{command}` のドキュメントが見つかりません。",
                color=discord.Color.red(),
            )
            metadata_commands = list(get_all_metadata().keys())
            if metadata_commands:
                embed.add_field(
                    name="利用可能なコマンド",
                    value=", ".join([f"`{cmd}`" for cmd in sorted(metadata_commands)]),
                    inline=False,
                )
        else:
            # Discord APIから取得した情報とメタデータを組み合わせて表示
            description_text = (
                cmd_obj.description if hasattr(cmd_obj, "description") else "説明なし"
            )
            embed = discord.Embed(
                title=f"{metadata.icon} /{command}",
                description=description_text,
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )

            # パラメータ情報を動的に生成
            if hasattr(cmd_obj, "parameters") and cmd_obj.parameters:
                params_text = []
                for param in cmd_obj.parameters:
                    param_name = param.name
                    param_desc = param.description or "説明なし"
                    required = "必須" if param.required else "任意"
                    params_text.append(f"**{param_name}** ({required}): {param_desc}")

                embed.add_field(
                    name="⚙️ パラメータ",
                    value="\n".join(params_text),
                    inline=False,
                )

            # メタデータからの追加情報
            if metadata.restrictions:
                embed.add_field(
                    name="🚫 実行制限",
                    value=metadata.restrictions,
                    inline=False,
                )

            if metadata.examples:
                embed.add_field(
                    name="💡 使用例",
                    value="\n".join(metadata.examples),
                    inline=False,
                )

            if metadata.notes:
                embed.add_field(name="📝 注意事項", value=metadata.notes, inline=False)

    if ctx.response.is_done():
        await ctx.followup.send(embed=embed, ephemeral=True)
    else:
        await ctx.response.send_message(embed=embed, ephemeral=True)
    logger.info(f"Docs command executed by {ctx.user}" + (f" for {command}" if command else ""))


# ==================== コマンド登録 ====================


def setup(tree: app_commands.CommandTree):
    """ヘルプコマンドを登録する

    デコレーターの順序（重要）:
    1. @command_meta() - メタデータの登録
    2. @tree.command() - コマンドの登録
    3. @app_commands.describe() - パラメータの説明
    """

    @command_meta(
        category="ヘルプ",
        icon="ℹ️",
        short_description="利用可能なコマンド一覧を表示",
        examples=["`/help`"],
    )
    @tree.command(
        name="help",
        description="Botのコマンド一覧を表示します",
    )
    async def help(ctx: discord.Interaction):
        await help_impl(ctx)

    @command_meta(
        category="ヘルプ",
        icon="ℹ️",
        short_description="コマンドの詳細ドキュメントを表示",
        examples=["`/docs`", "`/docs command:create_channel`"],
    )
    @tree.command(
        name="docs",
        description="コマンドの詳細ドキュメントを表示します",
    )
    @app_commands.describe(command="詳細を確認したいコマンド名（省略時は一覧を表示）")
    async def docs(ctx: discord.Interaction, command: str | None = None):
        await docs_impl(tree, ctx, command)
