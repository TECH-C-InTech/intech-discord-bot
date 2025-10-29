# intech-discord-bot

## ファイル構成

```
intech-discord-bot/
├── main.py                      # 旧エントリーポイント（レガシー）
├── bot.py                       # 新エントリーポイント（リファクタリング版）
├── src/
│   ├── __init__.py
│   ├── commands/                # コマンド定義
│   │   ├── __init__.py
│   │   └── event_channel.py    # イベントチャンネル管理コマンド
│   └── utils/                   # ユーティリティ関数
│       ├── __init__.py
│       ├── channel_utils.py    # チャンネル関連のユーティリティ
│       └── env_utils.py        # 環境変数関連のユーティリティ
├── .env                         # 環境変数（gitignore対象）
├── .env.sample                  # 環境変数のサンプル
├── pyproject.toml               # プロジェクト設定
└── README.md
```

## Setup

```bash
uv sync
```

.env.sampleをコピーして.envを作成し、環境変数を設定する。

```bash
cp .env.sample .env
```

discord bot tokenは @KorRyu3 or @nka21 に聞いてください。

## Usage

### リファクタリング版（推奨）

```bash
python bot.py
```

### レガシー版

```bash
python main.py
```

## 実装されているコマンド

### `/create_event_channel`
イベントチャンネルを作成します。

- **パラメータ:**
  - `channel_name`: 作成するイベントチャンネル名

- **機能:**
  - 既存のイベントチャンネルとアーカイブ済みチャンネルのインデックスを確認
  - 最大インデックス + 1 で新しいチャンネルを作成
  - チャンネル名は `{index}-{name}` の形式（例: `1-新歓イベント`）

### `/archive_event_channel`
イベントチャンネルをアーカイブします。

- **パラメータ:**
  - `channel_name` (任意): アーカイブするチャンネル名（省略時は実行チャンネル）

- **機能:**
  - 指定されたチャンネルをアーカイブカテゴリーに移動

## 環境変数

`.env` ファイルに以下の環境変数を設定してください：

- `DISCORD_BOT_TOKEN`: Discord Bot のトークン
- `EVENT_CATEGORY_NAME`: イベントカテゴリー名
- `ARCHIVE_EVENT_CATEGORY_NAME`: アーカイブカテゴリー名
- `EVENT_REQUEST_CHANNEL_NAME`: イベント作成リクエストを受け付けるチャンネル名

## 開発

### コマンドの追加方法

1. `src/commands/` に新しいファイルを作成
2. コマンド関数と `setup()` 関数を実装
3. `src/commands/__init__.py` でエクスポート
4. `bot.py` でセットアップ関数を呼び出す

### コードスタイル

- フォーマッター: ruff (または black)
- 型ヒントを推奨
- docstringを記述
