# セットアップガイド

## 📋 目次

1. [必要要件](#必要要件)
2. [セットアップ手順](#セットアップ手順)
3. [環境変数の設定](#環境変数の設定)
4. [Discord サーバーの設定](#discord-サーバーの設定)
5. [実行方法](#実行方法)
6. [トラブルシューティング](#トラブルシューティング)

## 必要要件

- **Python**: 3.11以上
- **uv**: Pythonパッケージマネージャー
- Discord Botトークン（管理者に問い合わせ）

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/TECH-C-InTech/intech-discord-bot.git
cd intech-discord-bot
```

### 2. 依存関係のインストール

```bash
uv sync
```

## 環境変数の設定

### 1. `.env` ファイルの作成

```bash
# Windows
copy .env.sample .env

# Linux/Mac
cp .env.sample .env
```

### 2. トークンの設定

`.env` ファイルを開いて `DISCORD_BOT_TOKEN` を設定:

```env
DISCORD_BOT_TOKEN=your_bot_token_here
EVENT_CATEGORY_NAME=event
ARCHIVE_EVENT_CATEGORY_NAME=archived-event
EVENT_REQUEST_CHANNEL_NAME=event-request
```

> **Note**: Bot Tokenは管理者（@KorRyu3 or @nka21）に問い合わせてください

### 3. 環境変数の説明

| 変数名 | 説明 | デフォルト例 |
|--------|------|--------------|
| `DISCORD_BOT_TOKEN` | Discord Botのトークン(Bot起動に必須) | - |
| `EVENT_CATEGORY_NAME` | イベントチャンネルを作成するカテゴリー名 | `event` |
| `ARCHIVE_EVENT_CATEGORY_NAME` | アーカイブ先のカテゴリー名 | `archived-event` |
| `EVENT_REQUEST_CHANNEL_NAME` | チャンネル作成リクエストを受け付けるチャンネル名 | `event-request` |

## Discord サーバーの設定

`.env` で設定した名前に合わせて、Discordサーバーに以下を作成:

### カテゴリー

1. `event` - イベントチャンネル用
2. `archived-event` - アーカイブ用

### チャンネル

1. `event-request` - チャンネル作成リクエスト用

### 構造例

```text
📁 event
├── # 1-新歓イベント
└── # 2-ハッカソン

📁 archived-event
└── # 3-終了したイベント

📁 その他
└── # event-request
```

## 実行方法

```bash
uv run bot.py
```

### 起動確認

正常に起動すると、以下のログが表示されます:

```text
INFO:__main__:Logged in as InTech Bot (ID: 1234567890)
INFO:__main__:------
INFO:__main__:Synced 2 command(s)
```

Discordで `/` を入力するとコマンドが表示されます。

## トラブルシューティング

### `DISCORD_BOT_TOKEN が設定されていません`

**解決方法:**

1. `.env` ファイルが存在するか確認
2. `DISCORD_BOT_TOKEN` が正しく設定されているか確認

### `カテゴリー 'event' が存在しません`

**解決方法:**

1. Discordサーバーでカテゴリーを作成
2. カテゴリー名と `.env` の設定を一致させる
3. Botを再起動

### `このコマンドは 'event-request' チャンネルでのみ実行できます`

**解決方法:**

`event-request` チャンネル（または `.env` で指定したチャンネル）で実行してください。

### `Botにチャンネルの作成する権限がありません`

**解決方法:**

1. Discordサーバー設定 → 役職 → Bot の役職
2. 「チャンネルの管理」権限を有効化

または、カテゴリーごとに権限を設定:

```text
カテゴリーを右クリック → 設定 → 権限 → Bot を追加 → 「チャンネルの管理」を許可
```

### コマンドが表示されない

**解決方法:**

1. Botを再起動して `Synced 2 command(s)` が表示されるか確認
2. Discordをリロード（Ctrl+R）
3. 30秒〜1分待ってから再度 `/` を入力

## サポート

問題が解決しない場合:

- GitHub Issues で質問
- Discord サーバーで開発者に連絡（@KorRyu3 or @nka21）
