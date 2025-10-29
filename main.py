import os
from logging import basicConfig, getLogger

import discord
from discord import app_commands
from dotenv import load_dotenv

logger = getLogger(__name__)
basicConfig(level="INFO")

load_dotenv()

# Discord Bot の設定
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@tree.command(description="新しいイベントチャンネルを作成します")
@app_commands.describe(
    channel_name="作成するイベントチャンネル名",
)
async def create_event_channel(
    ctx: discord.Interaction,
    channel_name: str,
):
    """イベントチャンネルを作成するコマンド"""

    event_category_name = os.getenv("EVENT_CATEGORY_NAME")
    if not event_category_name:
        await ctx.response.send_message(
            "❌ 環境変数 'EVENT_CATEGORY_NAME' が設定されていません。", ephemeral=True
        )
        return

    # コマンド実行チャンネルがEVENT_REQUEST_CHANNEL_NAMEか確認
    event_request_channel_name = os.getenv("EVENT_REQUEST_CHANNEL_NAME")
    if ctx.channel.name != event_request_channel_name:
        await ctx.response.send_message(
            f"❌ このコマンドは '{event_request_channel_name}' チャンネルでのみ実行できます。", ephemeral=True
        )
        return

    # eventカテゴリーが存在するか確認
    guild = ctx.guild
    category_channel = discord.utils.get(guild.categories, name=event_category_name)
    if not category_channel:
        logger.error(f"Event category '{event_category_name}' does not exist in guild '{guild.name}'")
        logger.error("Please update the EVENT_CATEGORY_NAME environment variable. now:", event_category_name)
        await ctx.response.send_message(
            f"❌ イベントカテゴリー '{event_category_name}' が存在しません。サーバー設定を更新する必要があるため、管理者に連絡してください。", ephemeral=True
        )
        return

    try:
        guild = ctx.guild

        channel = await guild.create_text_channel(
            name=channel_name, category=category_channel
        )

        # 成功メッセージ
        embed = discord.Embed(
            title="✅ イベントチャンネル作成完了",
            description=f"{channel.mention} を作成しました",
            color=discord.Color.green(),
        )
        embed.add_field(name="チャンネル名", value=channel_name, inline=True)

        await ctx.response.send_message(embed=embed)
        logger.info(f"Created channel: {channel_name} by {ctx.user}")

    except discord.Forbidden:
        await ctx.response.send_message(
            "❌ Botにチャンネルを作成する権限がありません。", ephemeral=True
        )
    except Exception as e:
        logger.error(f"Error creating channel: {e}")
        await ctx.response.send_message(
            f"❌ チャンネルの作成中にエラーが発生しました: {str(e)}", ephemeral=True
        )


# ARCHIVE_EVENT_CHANNELへの移動コマンド
@tree.command(description="イベントチャンネルをアーカイブします")
@app_commands.describe(
    channel_name="アーカイブするイベントチャンネル名(デフォルトはコマンド実行チャンネル)",
)
async def archive_event_channel(
    ctx: discord.Interaction,
    channel_name: str = None,
):
    """イベントチャンネルをアーカイブするコマンド"""

    archive_event_category_name = os.getenv("ARCHIVE_EVENT_CATEGORY_NAME")
    if not archive_event_category_name:
        await ctx.response.send_message(
            "❌ 環境変数 'ARCHIVE_EVENT_CATEGORY_NAME' が設定されていません。", ephemeral=True
        )
        return

    event_category_name = os.getenv("EVENT_CATEGORY_NAME")
    if not event_category_name:
        await ctx.response.send_message(
            "❌ 環境変数 'EVENT_CATEGORY_NAME' が設定されていません。", ephemeral=True
        )
        return

    # コマンド実行チャンネルがEVENT_REQUEST_CHANNEL_NAMEか確認
    event_request_channel_name = os.getenv("EVENT_REQUEST_CHANNEL_NAME")
    if ctx.channel.name == event_request_channel_name:
        await ctx.response.send_message(
            f"❌ このコマンドは '{event_request_channel_name}' チャンネルでは実行できません。", ephemeral=True
        )
        return


    guild = ctx.guild

    # アーカイブ先カテゴリーが存在するか確認
    archive_category_channel = discord.utils.get(
        guild.categories, name=archive_event_category_name
    )
    if not archive_category_channel:
        logger.error(f"Archive category '{archive_event_category_name}' does not exist in guild '{guild.name}'")
        logger.error("Please update the ARCHIVE_EVENT_CATEGORY_NAME environment variable. now:", archive_event_category_name)
        await ctx.response.send_message(
            f"❌ アーカイブカテゴリー '{archive_event_category_name}' が存在しません。サーバー設定を更新する必要があるため、管理者に連絡してください。", ephemeral=True
        )
        return

    # 移動するチャンネルを特定
    if channel_name:
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel:
            await ctx.response.send_message(
                f"❌ チャンネル '{channel_name}' が見つかりません。", ephemeral=True
            )
            return
    else:
        channel = ctx.channel

    # そのチャンネルはEVENT_CATEGORY_NAMEカテゴリーに属しているか確認
    event_category_name = os.getenv("EVENT_CATEGORY_NAME")
    if channel.category is None or channel.category.name != event_category_name:
        await ctx.response.send_message(
            f"❌ チャンネル '{channel.name}' はイベントカテゴリー '{event_category_name}' に属していません。\n"
            f"{event_category_name}配下のアーカイブしたいチャンネルでコマンドを実行するか、チャンネル名を指定してください。",
            ephemeral=True
        )
        return

    try:
        await channel.edit(category=archive_category_channel)

        # 成功メッセージ
        embed = discord.Embed(
            title="✅ イベントチャンネルアーカイブ完了",
            description=f"{channel.mention} をアーカイブしました",
            color=discord.Color.green(),
        )
        embed.add_field(name="チャンネル名", value=channel.name, inline=True)

        await ctx.response.send_message(embed=embed)
        logger.info(f"Archived channel: {channel.name} by {ctx.user}")

    except discord.Forbidden:
        await ctx.response.send_message(
            "❌ Botにチャンネルを編集する権限がありません。", ephemeral=True
        )
    except Exception as e:
        logger.error(f"Error archiving channel: {e}")
        await ctx.response.send_message(
            f"❌ チャンネルのアーカイブ中にエラーが発生しました: {str(e)}", ephemeral=True
        )


@client.event
async def on_ready():
    """Botが起動したときの処理"""
    logger.info(f"Logged in as {client.user} (ID: {client.user.id})")
    logger.info("------")

    # スラッシュコマンドを同期 (必須)
    try:
        synced = await tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")


def main():
    """メイン関数"""
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        logger.error("DISCORD_BOT_TOKEN が設定されていません")
        return

    client.run(token)


if __name__ == "__main__":
    main()
