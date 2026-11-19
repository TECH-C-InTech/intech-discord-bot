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


HELP_TITLE = "🤖 InTechボットの使い方"

HELP_DESCRIPTION = (
    "クラブ・イベント・プロジェクトの作成や、参加の切り替えができます。\n"
    "基本的に操作はボタンで完結します。迷ったら、どこでも`/intech`と打ってください。"
)

# コマンドではなく、メンバーのやりたいことごとに案内する
HELP_SECTIONS = [
    (
        "🌱 操作可能なチャンネルの種類",
        "- クラブ：共通の興味でゆるく集まる、常設の趣味部屋\n"
        "- イベント：一回きりの集まり。「ここ行きたい」くらいの思いつきで作っちゃってOK\n"
        "- プロジェクト：一定期間続く活動全般",
    ),
    (
        "✨ チャンネルを作りたい",
        "一番上のINFORMATIONカテゴリにある {create_channel} を開き、"
        "「イベントを作る」などのボタンを押して、チャンネル名を入れて送信するだけです。\n"
        "（クラブ・イベント・プロジェクト以外のチャンネルで`/intech`と打っても同じ操作ができます）",
    ),
    (
        "🙋 参加したい・抜けたい",
        "当該チャンネル右上の📌（ピン留め）にある「参加する」「抜ける」を押します。"
        "参加すると、そのチャンネルの参加者あてのメンション（@e001など）が届くようになります。",
    ),
    (
        "👥 ほかの人を追加したい・外したい",
        "ピン留めの「参加者を追加」「参加者を外す」から選びます。",
    ),
    (
        "📦 終わったので片付けたい",
        "ピン留めの「アーカイブ」を押すと、チャンネルが目立たない場所"
        "（一番下のアーカイブカテゴリ）へ移ります。チャンネルは消えません。",
    ),
    (
        "↩️ アーカイブ後にまた使いたい",
        "アーカイブしたチャンネルにメッセージを送るだけで、元のカテゴリに戻ります。",
    ),
    (
        "👀 誰が参加しているか見たい",
        "ピン留めのパネルから参加者一覧が見られます。",
    ),
]

HELP_FOOTER = "コマンドで操作したい人は /docs で使い方を確認してください。"

# 作るパネルを置いている案内チャンネル。見つかればリンクにする
CREATE_CHANNEL_NAME = "create_channel"


def _create_channel_text(guild: discord.Guild | None) -> str:
    channel = discord.utils.get(guild.text_channels, name=CREATE_CHANNEL_NAME) if guild else None
    return channel.mention if channel else f"#{CREATE_CHANNEL_NAME}"


async def help_impl(ctx: discord.Interaction):
    """ボットの使い方を、やりたいことごとに案内する"""
    embed = discord.Embed(
        title=HELP_TITLE,
        description=HELP_DESCRIPTION,
        color=discord.Color.blue(),
    )
    create_channel = _create_channel_text(ctx.guild)
    for name, value in HELP_SECTIONS:
        embed.add_field(name=name, value=value.format(create_channel=create_channel), inline=False)
    embed.set_footer(text=HELP_FOOTER)

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
        all_metadata = get_all_metadata()
        if all_metadata:
            available_commands = "\n".join(
                f"• `/docs command:{cmd}`"
                + (f" - {meta.short_description}" if meta.short_description else "")
                for cmd, meta in sorted(all_metadata.items())
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
        short_description="ボットの使い方を、やりたいことごとに表示",
        examples=["`/help`"],
    )
    @tree.command(
        name="help",
        description="ボットの使い方を表示します",
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
