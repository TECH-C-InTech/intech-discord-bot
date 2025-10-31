# 開発ガイド

このドキュメントでは、開発ワークフロー、コードスタイル、CI/CDパイプラインについて説明します。

## 📋 目次

1. [開発環境のセットアップ](#開発環境のセットアップ)
2. [開発ワークフロー](#開発ワークフロー)
3. [コードスタイル](#コードスタイル)
4. [コード品質チェック](#コード品質チェック)
5. [CI/CDパイプライン](#cicdパイプライン)
6. [デプロイ](#デプロイ)

## 開発環境のセットアップ

### 必要なツール

- **Python 3.11+**
- **uv** - Pythonパッケージマネージャー
- **Git**
- Discord Botトークン（開発用と本番用を分ける）

### 初期セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/TECH-C-InTech/intech-discord-bot.git
cd intech-discord-bot

# 依存関係をインストール（開発モード）
uv sync --dev
```

### 環境変数の設定

#### 開発環境

開発とテストをスムーズに行うため、**開発用Botと本番用Botを分けること**を推奨します。

```bash
# .env.dev.sampleをコピー
cp .env.dev.sample .env.dev
```

`.env.dev`を編集:
```env
DISCORD_BOT_TOKEN=your_dev_bot_token_here
DEV_GUILD_ID=your_dev_server_id_here
EVENT_CATEGORY_NAME=event
ARCHIVE_EVENT_CATEGORY_NAME=archived
EVENT_REQUEST_CHANNEL_NAME=event-request
```

**推奨構成**:

| 環境 | Bot | Token | DEV_GUILD_ID | 用途 |
|------|-----|-------|--------------|------|
| ローカル開発 | InTech_dev | 開発用 | 開発サーバーID | 手元でのテスト |
| デプロイ（本番） | InTech | 本番用 | (空) | 本番運用 |

#### DEV_GUILD_IDのメリット

- **コマンドの即座反映** - グローバル同期は最大1時間かかるが、ギルド同期は即座
- **本番環境への影響なし** - 開発中のコマンドが本番に表示されない
- **安全なテスト** - 本番サーバーに影響を与えずにテスト可能

#### DEV_GUILD_IDの取得方法

1. Discordで開発者モードを有効化
   - 設定 → 詳細設定 → 開発者モード をON
2. 開発用サーバーを右クリック → 「サーバーIDをコピー」
3. `.env.dev` ファイルに `DEV_GUILD_ID="コピーしたID"` を追加

## 開発ワークフロー

### Botの起動

```bash
# 開発モード（.env.devを使用、即座にコマンド同期）
uv run bot.py --env .env.dev

# 本番モード（.envを使用、グローバル同期）
uv run bot.py
```

### ブランチ戦略

```bash
# 機能ブランチを作成
git checkout -b feature/new-command

# 変更をコミット
git add .
git commit -m "feat: 新しいコマンドを追加"

# プルリクエストを作成
git push origin feature/new-command
```

**コミットメッセージの規則**:
- `feat:` - 新機能
- `fix:` - バグ修正
- `docs:` - ドキュメントの変更
- `refactor:` - リファクタリング
- `test:` - テストの追加・修正
- `chore:` - その他の変更

### 新しいコマンドの追加

詳細は [ADD_COMMAND.md](./ADD_COMMAND.md) を参照してください。

**クイックステップ**:
1. [src/commands/_sample.py](../src/commands/_sample.py) をコピー
2. `src/commands/your_command.py` にリネーム
3. コマンドロジックを実装
4. `@command_meta()` デコレーターでメタデータを追加
5. 開発環境でテスト
6. プルリクエストを作成

## コードスタイル

### Ruff設定

設定ファイル: [ruff.toml](../ruff.toml)

**主要なルール**:
- **行の長さ**: 100文字まで
- **Pythonバージョン**: 3.11+
- **クォートスタイル**: ダブルクォート (`"`)
- **インデント**: 4スペース
- **型ヒント**: 必須（mypyでチェック）
- **モダン構文**: Union型には `|` を使用（例: `str | None`）

### コーディング規約

#### 型ヒント

```python
# ✅ 良い例
async def create_channel(
    ctx: discord.Interaction,
    name: str,
    members: str | None = None
) -> discord.TextChannel:
    """チャンネルを作成"""
    pass

# ❌ 悪い例
async def create_channel(ctx, name, members=None):
    """チャンネルを作成"""
    pass
```

#### docstring

```python
# ✅ 良い例
def parse_member_mentions(ctx: discord.Interaction, mention_string: str | None) -> list[discord.Member]:
    """メンション文字列を解析してMemberオブジェクトのリストに変換

    Args:
        ctx: Discordインタラクション
        mention_string: メンション文字列（例: "@user1 @user2"）

    Returns:
        Memberオブジェクトのリスト
    """
    pass
```

#### インポート順序

```python
# 1. 標準ライブラリ
from logging import getLogger
import re

# 2. サードパーティライブラリ
import discord
from discord import app_commands

# 3. ローカルモジュール
from ..utils.command_metadata import command_meta
from ..utils.validation_utils import validate_channel_restriction
```

## コード品質チェック

### フォーマット

```bash
# コードをフォーマット
uv run ruff format .

# フォーマットチェック（CIで実行）
uv run ruff format --check .
```

### リント

```bash
# リントチェック
uv run ruff check .

# 自動修正可能な問題を修正
uv run ruff check --fix .
```

**チェック項目**:
- `E` - pycodestyle エラー
- `F` - Pyflakes
- `W` - pycodestyle 警告
- `I` - isort（インポート順序）
- `B` - flake8-bugbear
- `N` - pep8-naming

### 型チェック

```bash
# 型チェック
uv run mypy .
```

### プルリクエスト前のチェックリスト

```bash
# すべてのチェックを実行
uv run ruff format --check .
uv run ruff check .
uv run mypy .

# または自動修正してからチェック
uv run ruff format .
uv run ruff check --fix .
uv run mypy .
```

## CI/CDパイプライン

### Lintワークフロー

**ファイル**: [.github/workflows/lint.yml](../.github/workflows/lint.yml)

**トリガー**: プルリクエスト作成時

**実行内容**:
1. Python 3.11環境をセットアップ
2. uvをインストール
3. 依存関係をインストール (`uv sync --dev`)
4. フォーマットチェック (`ruff format --check`)
5. リントチェック (`ruff check`)
6. 型チェック (`mypy`)

**すべてのチェックが通らないとマージできません。**

### Deployワークフロー

**ファイル**: [.github/workflows/fly-deploy.yml](../.github/workflows/fly-deploy.yml)

**トリガー**: `main` ブランチへのプッシュ

**実行内容**:
1. Fly.io CLIをセットアップ
2. Dockerイメージをビルド
3. Fly.ioにデプロイ（東京リージョン）

**環境変数**:
- `FLY_API_TOKEN` - GitHub Secretsに設定

## デプロイ

### Fly.io設定

**設定ファイル**: [fly.toml](../fly.toml)

**リソース**:
- **リージョン**: Tokyo (NRT)
- **CPU**: 1 shared CPU
- **メモリ**: 1GB RAM
- **自動起動**: 有効
- **ヘルスチェック**: HTTP (FastAPIサーバー経由)

### デプロイコマンド

```bash
# 手動デプロイ
fly deploy

# ログを表示
flyctl logs

# ステータスを確認
flyctl status
```

### 初回セットアップ（管理者のみ）

```bash
# Fly.ioにログイン
fly auth login

# アプリを作成（東京リージョン）
flyctl launch --region nrt

# 環境変数を設定
fly secrets set DISCORD_BOT_TOKEN="your_token_here"
fly secrets set EVENT_CATEGORY_NAME="event"
fly secrets set ARCHIVE_EVENT_CATEGORY_NAME="archived"
fly secrets set EVENT_REQUEST_CHANNEL_NAME="event-request"

# デプロイ
fly deploy
```

### 自動デプロイの流れ

1. `main` ブランチへのプッシュ/マージ
2. GitHub Actionsがデプロイワークフローをトリガー
3. Fly.ioがDockerイメージをビルド
4. 新しいインスタンスが東京リージョンにデプロイ
5. ヘルスチェックでデプロイメントを検証
6. 問題なければ古いインスタンスを停止

### トラブルシューティング

#### デプロイが失敗する

```bash
# ログを確認
flyctl logs

# ステータスを確認
flyctl status

# ローカルでDockerイメージをテスト
docker build -t intech-bot .
docker run -p 8000:8000 intech-bot
```

#### コマンドが同期されない

- グローバル同期は最大1時間かかります
- 開発時は `DEV_GUILD_ID` を使用して即座に同期
- Botのログで `Synced X command(s)` を確認

## テスト戦略

**現在、自動テストはありません** - 環境分離によるマニュアルテスト:

- 開発環境: `DEV_GUILD_ID` で迅速なイテレーション
- 本番環境: グローバルコマンド同期
- 別々のBotトークンで干渉を防ぐ

### 手動テストの手順

1. `.env.dev` で開発環境を設定
2. `uv run bot.py --env .env.dev` でBotを起動
3. 開発サーバーでコマンドをテスト
4. エラーがないことを確認
5. プルリクエストを作成
6. CI チェックが通ることを確認
7. マージ後、本番環境で動作確認

## 関連ドキュメント

- [コマンド追加方法](./ADD_COMMAND.md) - 新しいコマンドの追加手順
- [アーキテクチャガイド](./ARCHITECTURE.md) - システムアーキテクチャの詳細
- [ユーティリティ関数](./UTILITIES.md) - 共通ユーティリティの使い方
- [セットアップガイド](./SETUP.md) - 環境構築の詳細手順
