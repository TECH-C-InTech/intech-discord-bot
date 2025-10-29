# 開発環境セットアップガイド

## 問題

開発サーバーにプロダクション用BotとローカルBotの両方が存在し、テストがしづらい。

## 解決策

### 🎯 方法1: 別々のBotアプリケーションを使用（推奨）

Discord Developer Portalで**開発専用のBotアプリケーション**を作成します。

#### メリット
- ✅ プロダクションBotとローカルBotが完全に分離
- ✅ コマンド名の衝突がない
- ✅ 本番環境に影響を与えずにテスト可能
- ✅ 開発サーバーでどちらのBotを使うか明確

#### 手順

1. **Discord Developer Portalで新しいアプリケーションを作成**
   - https://discord.com/developers/applications
   - `InTech Bot (Dev)` のような名前で作成

2. **Bot Tokenを取得**
   - Botタブで新しいBotを作成
   - Tokenをコピー

3. **開発用の環境変数を設定**

   `.env.dev` ファイルを作成:
   ```bash
   # 開発用Bot Token
   DISCORD_BOT_TOKEN="開発用Botのトークン"
   
   # 開発サーバーID
   DEV_GUILD_ID="開発サーバーのID"
   
   # イベントチャンネル管理用の設定
   EVENT_CATEGORY_NAME="event"
   ARCHIVE_EVENT_CATEGORY_NAME="archived"
   EVENT_REQUEST_CHANNEL_NAME="event-request"
   
   # Keep-aliveサーバー設定
   PORT="8000"
   ```

4. **開発用Botを開発サーバーに招待**
   ```
   https://discord.com/api/oauth2/authorize?client_id=開発BotのクライアントID&permissions=8&scope=bot%20applications.commands
   ```

5. **起動時に環境ファイルを指定**

    ```bash
   # 開発環境
   uv run bot.py --env .env.dev

   # または環境変数で指定
   ENV_FILE=.env.dev uv run bot.py
    ```

#### bot.pyの修正

```python
import argparse
from dotenv import load_dotenv

# コマンドライン引数で環境ファイルを指定可能に
parser = argparse.ArgumentParser()
parser.add_argument('--env', default='.env', help='環境ファイルのパス')
args, unknown = parser.parse_known_args()

# 指定された環境ファイルを読み込む
env_file = os.getenv('ENV_FILE', args.env)
load_dotenv(env_file)
logger.info(f"Loaded environment from: {env_file}")
```

### 🔧 方法2: コマンドプレフィックスを使用

開発Botのコマンドに `_dev` サフィックスを付ける。

#### メリット
- ✅ 1つのBotアプリケーションで済む
- ✅ コマンドの衝突を回避

#### デメリット
- ❌ コマンド名が長くなる
- ❌ 開発と本番でコード差分が生じる

#### 実装

```python
# bot.py
import os
from dotenv import load_dotenv

load_dotenv()

# 環境に応じてコマンドプレフィックスを設定
COMMAND_PREFIX = "_dev" if os.getenv("IS_DEV_MODE", "false").lower() == "true" else ""

# コマンド登録時にプレフィックスを追加
@tree.command(
    name=f"create_event_channel{COMMAND_PREFIX}",
    description="新しいイベントチャンネルを作成します"
)
async def create_event_channel_cmd(...):
    ...
```

**.env.dev**:
```bash
IS_DEV_MODE="true"
DISCORD_BOT_TOKEN="同じBotトークン"
DEV_GUILD_ID="開発サーバーのID"
```

### 🌐 方法3: 開発専用サーバーを用意

開発専用の別のDiscordサーバーを作成する。

#### メリット
- ✅ 完全に分離されたテスト環境
- ✅ 本番環境を汚さない

#### デメリット
- ❌ 別サーバーの管理が必要
- ❌ 本番に近い環境でのテストができない

## 📝 推奨構成

### 環境ごとのファイル構成

```
intech-discord-bot/
├── .env                # ローカル開発用（gitignore）
├── .env.dev            # 開発サーバー用（gitignore）
├── .env.prod           # 本番環境用（gitignore）
├── .env.sample         # サンプル
└── bot.py
```

### 環境変数の使い分け

| 環境 | ファイル | Bot Token | DEV_GUILD_ID | 用途 |
|------|---------|-----------|--------------|------|
| **ローカル開発** | `.env` | 開発用Bot | 開発サーバーID | 手元でのテスト |
| **デプロイ（開発）** | 環境変数 | 開発用Bot | 開発サーバーID | デプロイ版開発Bot |
| **デプロイ（本番）** | 環境変数 | 本番用Bot | (未設定) | 本番環境 |

## 🚀 実装例: 方法1（推奨）

### 1. bot.pyを修正

```python
"""Discord Bot エントリーポイント"""

import asyncio
import os
import argparse
from logging import basicConfig, getLogger

import discord
from discord import app_commands
from dotenv import load_dotenv

from keep_alive import run_server_async
from src.commands import setup_all_commands

logger = getLogger(__name__)
basicConfig(level="INFO")

# 環境ファイルの読み込み
parser = argparse.ArgumentParser()
parser.add_argument('--env', default='.env', help='環境ファイルのパス')
args, unknown = parser.parse_known_args()

env_file = os.getenv('ENV_FILE', args.env)
load_dotenv(env_file)
logger.info(f"📝 Loaded environment from: {env_file}")

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
    # Bot情報を表示
    bot_mode = "DEVELOPMENT" if os.getenv("DEV_GUILD_ID") else "PRODUCTION"
    logger.info(f"🤖 Bot Name: {client.user} (ID: {client.user.id})")
    logger.info(f"🔧 Mode: {bot_mode}")
    logger.info("------")

    # スラッシュコマンドを同期
    try:
        dev_guild_id = os.getenv("DEV_GUILD_ID")

        if dev_guild_id:
            # 開発サーバーのみに同期（即座に反映）
            guild = discord.Object(id=int(dev_guild_id))
            tree.copy_global_to(guild=guild)
            synced = await tree.sync(guild=guild)
            logger.info(
                f"✅ [DEV MODE] Synced {len(synced)} command(s) to development guild (ID: {dev_guild_id})"
            )
        else:
            # 全サーバーに同期（反映に最大1時間かかる）
            synced = await tree.sync()
            logger.info(f"✅ [PRODUCTION] Synced {len(synced)} command(s) globally")

    except Exception as e:
        logger.error(f"❌ Failed to sync commands: {e}")


async def run_bot():
    """Botを非同期で実行"""
    # 全てのコマンドを一括セットアップ
    setup_all_commands(tree)

    # Botを起動
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        logger.error("❌ DISCORD_BOT_TOKEN が設定されていません")
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
```

### 2. .env.sample を更新

```bash
# Bot Token（開発用Botと本番用Botで別々のTokenを使用）
DISCORD_BOT_TOKEN="Your discord bot token"

# イベントチャンネル管理用の設定
EVENT_CATEGORY_NAME="event"
ARCHIVE_EVENT_CATEGORY_NAME="archived"
EVENT_REQUEST_CHANNEL_NAME="event-request"

# 開発環境設定
# ローカル開発時: 開発サーバーのIDを設定
# 本番環境: 空にする（全サーバーに同期）
DEV_GUILD_ID=""

# Keep-aliveサーバー設定
PORT="8000"
```

### 3. 使い方

```bash
uv run bot.py --env .env.dev
```

## 📋 チェックリスト

### 開発用Botの作成
- [ ] Discord Developer Portalで開発用Botアプリケーションを作成
- [ ] 開発用BotのTokenを取得
- [ ] `.env.dev` ファイルを作成
- [ ] 開発用Botを開発サーバーに招待
- [ ] ローカルで開発用Botを起動してテスト

### デプロイ設定
- [ ] デプロイ環境（Render/Railwayなど）に環境変数を設定
  - `DISCORD_BOT_TOKEN`: 開発用または本番用
  - `DEV_GUILD_ID`: 開発環境のみ設定
- [ ] デプロイ後、コマンドが正しく同期されているか確認

## 💡 ベストプラクティス

1. **Bot命名規則**
   - 本番: `InTech`
   - 開発: `InTech_dev`

2. **アイコンで識別**
   - 開発用Botには異なるアイコンを設定

3. **ロール権限**
   - 開発Botには最小限の権限のみ付与
   - 本番Botには必要な権限を付与

4. **ログレベル**
   - 開発: `DEBUG`
   - 本番: `INFO` または `WARNING`

## 🔍 トラブルシューティング

### Q: 両方のBotが同時に反応する

A: 以下を確認：
- 開発用Botと本番用Botで異なるTokenを使用しているか
- `DEV_GUILD_ID` が正しく設定されているか
- デプロイ環境の環境変数が正しいか

## 参考リンク

- [Discord Developer Portal](https://discord.com/developers/applications)
- [Discord.py ドキュメント](https://discordpy.readthedocs.io/)
