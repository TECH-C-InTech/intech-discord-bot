"""Discord Bot エントリーポイント (リファクタリング版)"""

import os
from logging import basicConfig, getLogger

import discord
from discord import app_commands
from dotenv import load_dotenv

from src.commands import setup_all_commands

logger = getLogger(__name__)
basicConfig(level="INFO")

load_dotenv()

# Discord Bot の設定
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


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
    # 全てのコマンドを一括セットアップ
    setup_all_commands(tree)

    # Botを起動
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        logger.error("DISCORD_BOT_TOKEN が設定されていません")
        return

    client.run(token)


if __name__ == "__main__":
    main()
