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
ARCHIVE_EVENT_CATEGORY_NAME=archived
PROJECT_CATEGORY_NAME=project
ARCHIVE_PROJECT_CATEGORY_NAME=archived-project
CLUB_CATEGORY_NAME=clubs
ARCHIVE_CLUB_CATEGORY_NAME=archived-clubs
```

> **Note**: Bot Tokenは管理者（@KorRyu3 or @nka21）に問い合わせてください

### 3. 環境変数の説明

`DISCORD_BOT_TOKEN`以外は、すべて設定しないとコマンドが設定エラーになります。

| 変数名 | 説明 | 例 |
|--------|------|------|
| `DISCORD_BOT_TOKEN` | Discord Botのトークン(Bot起動に必須) | - |
| `EVENT_CATEGORY_NAME` | イベントチャンネルを作成するカテゴリー名 | `event` |
| `ARCHIVE_EVENT_CATEGORY_NAME` | イベントのアーカイブ先のカテゴリー名 | `archived` |
| `PROJECT_CATEGORY_NAME` | プロジェクトチャンネルを作成するカテゴリー名 | `project` |
| `ARCHIVE_PROJECT_CATEGORY_NAME` | プロジェクトのアーカイブ先のカテゴリー名 | `archived-project` |
| `CLUB_CATEGORY_NAME` | クラブチャンネルを作成するカテゴリー名 | `clubs` |
| `ARCHIVE_CLUB_CATEGORY_NAME` | クラブのアーカイブ先のカテゴリー名 | `archived-clubs` |

## Discord サーバーの設定

`.env` で設定した名前に合わせて、Discordサーバーに以下を作成:

### カテゴリー

1. `event` - イベントチャンネル用
2. `archived` - イベントのアーカイブ用
3. `project` - プロジェクトチャンネル用
4. `archived-project` - プロジェクトのアーカイブ用
5. `clubs` - クラブチャンネル用
6. `archived-clubs` - クラブのアーカイブ用

アーカイブ用のカテゴリは種類ごとに分けてください（アーカイブ後に種類の番号順で並べ直すため）。botは各カテゴリのチャンネルに記録を投稿するため、上のカテゴリすべてでbotが閲覧・送信・埋め込みリンクできるようにしてください。アーカイブ用のカテゴリは、対応する通常のカテゴリと同じ権限にしてください（アーカイブ中のチャンネルに投稿すると自動で復元されるため、メンバーが送信できる必要があります）。botはアーカイブ・復元のときにカテゴリの権限をチャンネルに写しますが、botが持っていない権限の許可・拒否がカテゴリにあると写せません。そうした設定をする場合は、そのカテゴリでbotに「権限の管理」を個別に付与してください。

### パネル

コマンドを知らないメンバー向けに、ボタンで操作できるパネルを置きます（[CHANNELS.md](./CHANNELS.md#パネル)）。

1. botのロールに、サーバー全体で「メッセージをピン留め」権限を付ける（「メッセージの管理」とは別の権限）。チャンネルのパネルをピン留めするため。ピン留めできないとパネルが書き換わりません（botはピン留めからパネルを探して書き換えるため）。その場合パネルは投稿されたまま残るので、手でピン留めしてください
2. 案内用のチャンネル（例: `はじめに-チャンネルを作る`）で `/setup_panel panel:作るパネル（このチャンネルに置く）` を実行する
3. 既存のクラブ・イベント・プロジェクトのチャンネルに `/setup_panel panel:すべてのチャンネルのパネル` でまとめて置く（すでにパネルがあるチャンネルと、番号でロールと紐づかないチャンネルは飛ばす）。新しく作ったチャンネルには自動で置かれます

`/setup_panel` はサーバーの管理権限を持つ人にだけ表示されます。

### 構造例

```text
📁 event
├── # e001-新歓イベント
└── # e002-ハッカソン

📁 archived
└── # e003-終了したイベント
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

### `必要な環境変数が設定されていません`

コマンドを実行すると、不足している環境変数が一覧で表示されます。

**解決方法:**

1. 表示された環境変数を `.env` に追加
2. Botを再起動

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
