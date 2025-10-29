"""Discord Bot エントリーポイント"""

import asyncio
import os
from logging import basicConfig, getLogger

import discord
from discord import app_commands
from dotenv import load_dotenv

from keep_alive import run_server_async
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
        # 開発用サーバーIDが設定されている場合、そのサーバーのみに同期
        dev_guild_id = os.getenv("DEV_GUILD_ID")

        if dev_guild_id:
            # 開発サーバーのみに同期（即座に反映）
            guild = discord.Object(id=int(dev_guild_id))
            tree.copy_global_to(guild=guild)
            synced = await tree.sync(guild=guild)
            logger.info(
                f"[DEV MODE] Synced {len(synced)} command(s) to development guild (ID: {dev_guild_id})"
            )
        else:
            # 全サーバーに同期（反映に最大1時間かかる）
            synced = await tree.sync()
            logger.info(f"[PRODUCTION] Synced {len(synced)} command(s) globally")

    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")


async def run_bot():
    """Botを非同期で実行"""
    # 全てのコマンドを一括セットアップ
    setup_all_commands(tree)

    # Botを起動
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        logger.error("DISCORD_BOT_TOKEN が設定されていません")
        return

    await client.start(token)


async def main():
    """メイン関数"""
    # Keep-aliveサーバーのポート（環境変数から取得、デフォルトは8000）
    port = int(os.getenv("PORT", "8000"))

    # Keep-aliveサーバーとBotを並行して実行
    await asyncio.gather(
        run_server_async(host="0.0.0.0", port=port),
        run_bot(),
    )


if __name__ == "__main__":
    asyncio.run(main())
