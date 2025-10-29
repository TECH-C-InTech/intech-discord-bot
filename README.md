# intech-discord-bot

## ファイル構成

```
intech-discord-bot/
├── bot.py                       # エントリーポイント
├── src/
│   ├── __init__.py
│   ├── commands/                # コマンド定義
│   └── utils/                   # ユーティリティ関数
├── .env                         # 環境変数（gitignore対象）
├── .env.sample                  # 環境変数のサンプル
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

discord bot tokenは @KorRyu3 or @nka21 に聞いてください。

## Usage

### 実行

```bash
python bot.py
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
3. `.env` ファイルに `DEV_GUILD_ID="コピーしたID"` を追加

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
