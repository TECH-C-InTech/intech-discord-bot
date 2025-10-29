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

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# デコレーターが続く場合、関数名を拾えないので、nameで明示的に指定してやる
@tree.command(name='hello', description="挨拶をします")
@app_commands.describe(user="挨拶するユーザー")
async def hello(ctx: discord.Interaction):
    """シンプルな挨拶コマンド"""
    await ctx.response.send_message(
        f"こんにちは、{ctx.user.mention}さん！"
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
