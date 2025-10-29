# intech-discord-bot

## ファイル構成

```
intech-discord-bot/
├── bot.py                       # エントリーポイント
├── src/
│   ├── __init__.py
│   ├── commands/                # コマンド定義
│   └── utils/                   # ユーティリティ関数
├── .env.sample                  # 環境変数のサンプル
├── .env.dev.sample              # 開発環境用環境変数のサンプル
├── pyproject.toml               # プロジェクト設定
└── README.md
```

## Setup

```bash
uv sync --dev
```

.env.sampleをコピーして.envを作成し、環境変数を設定する。

```bash
cp .env.sample .env
```

開発用には.env.dev.sampleをコピーして.env.devを作成する。

```bash
cp .env.dev.sample .env.dev
```

discord bot tokenは @KorRyu3 に聞いてください。

## Usage

### 🚀 クイックスタート

#### ローカル開発

```bash
# 開発用環境ファイルを指定
uv run bot.py --env .env.dev
```

#### 開発環境と本番環境の分離

開発とテストをスムーズに行うため、**開発用Botと本番用Botを分けること**を推奨します。

**推奨構成:**

| 環境 | Bot | Token | DEV_GUILD_ID | 用途 |
|------|-----|-------|--------------|------|
| ローカル開発 | InTech_dev | 開発用 | 開発サーバーID | 手元でのテスト |
| デプロイ（本番） | InTech | 本番用 | (空) | 本番運用 |

**セットアップ手順:**

1. Discord Developer Portalで開発用Botアプリケーションを作成
2. `.env.dev.sample` をコピーして `.env.dev` を作成
3. 開発用BotのTokenと開発サーバーIDを設定
4. `uv run bot.py --env .env.dev` で起動

詳細は `docs/DEV_SETUP.md` を参照してください。

### 実行

```bash
uv run bot.py
```

## 実装されているコマンド

## 📖 コマンド

| コマンド | 説明 |
|---------|------|
| `/help` | コマンド一覧を表示 |
| `/docs [command]` | コマンドの詳細ドキュメントを表示 |
| `/create_event_channel <name> [members]` | イベントチャンネルとロールを作成 |
| `/archive_event_channel [name]` | イベントチャンネルをアーカイブ |
| `/restore_event_channel [name]` | アーカイブされたチャンネルを復元 |
| `/add_event_role_member <members> [role_name]` | イベントロールにメンバーを追加 |
| `/show_role_members <role_name> [visibility]` | ロールのメンバー一覧を表示 |

> 💡 各コマンドの詳細は `/docs command:コマンド名` で確認できます

## 環境変数

`.env` ファイルに以下の環境変数を設定してください：

### 必須

- `DISCORD_BOT_TOKEN`: Discord Bot のトークン

### イベントチャンネル管理

- `EVENT_CATEGORY_NAME`: イベントカテゴリー名
- `ARCHIVE_EVENT_CATEGORY_NAME`: アーカイブカテゴリー名
- `EVENT_REQUEST_CHANNEL_NAME`: イベント作成リクエストを受け付けるチャンネル名

### 開発環境（任意）

- `DEV_GUILD_ID`: 開発用サーバーのID（設定すると、このサーバーのみにコマンドを同期）

### デプロイ環境（任意）

- `PORT`: Keep-aliveサーバーのポート番号（デフォルト: 8000）

### 開発サーバーIDの取得方法

1. Discordで開発者モードを有効化
   - 設定 → 詳細設定 → 開発者モード をON
2. 開発用サーバーを右クリック → 「サーバーIDをコピー」
3. `.env.dev` ファイルに `DEV_GUILD_ID="コピーしたID"` を追加

**開発時のメリット:**

- コマンドの反映が即座（グローバル同期は最大1時間）
- 本番サーバーに影響を与えずにテスト可能

## 開発

### コマンドの追加方法

1. `src/commands/` に新しいファイルを作成
2. コマンド関数と `setup()` 関数を実装
3. `@command_meta()` デコレーターでメタデータを登録（カテゴリー、アイコン、説明など）
4. ファイルを保存すれば自動的に登録されます

**詳細は `docs/ADD_COMMAND.md` を参照してください。**

#### テンプレート

`src/commands/_sample.py` にテンプレートがあります。

### コードスタイル

- フォーマッター: ruff
- 型ヒントを推奨
- docstringを記述

## Deployment

Fly.ioにデプロイしています。

```bash
fly deploy

# logs
flyctl logs

# status
flyctl status
```

※ 初回オンリー

```bash
fly auth login
flyctl launch --region nrt
fly deploy
fly secrets set { .env.sampleの内容をここにコピー }
fly deploy
```
