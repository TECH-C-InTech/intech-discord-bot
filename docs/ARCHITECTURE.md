# アーキテクチャガイド

このドキュメントでは、InTech Discord Botの技術スタックとアーキテクチャパターンについて説明します。

## 📋 目次

1. [技術スタック](#技術スタック)
2. [アーキテクチャパターン](#アーキテクチャパターン)
3. [コマンド登録システム](#コマンド登録システム)
4. [設定管理](#設定管理)
5. [イベントチャンネルのインデックス管理](#イベントチャンネルのインデックス管理)

## 技術スタック

- **言語**: Python 3.11+
- **Discordフレームワーク**: discord.py 2.6.4+ (モダンなスラッシュコマンド with `app_commands`)
- **Webサーバー**: FastAPI + uvicorn (Keep-alive用ヘルスチェックサーバー)
- **パッケージマネージャー**: `uv` (モダンなPythonパッケージマネージャー)
- **デプロイ**: Fly.io (東京リージョン、Docker ベース)

## アーキテクチャパターン

### デュアルサーバーアーキテクチャ

Botは2つの並列サーバーを実行します:

1. **Discord Bot** ([bot.py](../bot.py)) - スラッシュコマンドを持つメインのDiscordクライアント
2. **FastAPI Server** ([keep_alive.py](../keep_alive.py)) - ヘルスチェックエンドポイント (`/`, `/health`, `/ping`)

両方のサーバーは[bot.py](../bot.py)内で`asyncio.gather()`を使用して実行されます。これにより、HTTPエンドポイントを必要とするプラットフォーム(Fly.ioなど)へのデプロイが可能になります。

**実装コード** ([bot.py](../bot.py)):
```python
async def main():
    async with bot:
        # Discord BotとFastAPIサーバーを並列実行
        await asyncio.gather(
            bot.start(token),
            run_keep_alive()
        )
```

### ステートレス設計

**データベース不要** - すべての状態はDiscord上に存在:

- チャンネル、ロール、カテゴリーが唯一の真実の情報源
- Botを再起動してもデータ損失なし
- 設定は環境変数から取得

この設計により、以下のメリットがあります:
- シンプルな構成（DBサーバー不要）
- 高い可用性（状態同期の問題なし）
- 簡単なバックアップ（Discordが管理）

## コマンド登録システム

**これがコードベースで最も重要なアーキテクチャパターンです。**

### 自動検出と登録

コマンドは起動時に自動検出・登録されます:

1. **場所**: [src/commands/\_\_init\_\_.py](../src/commands/__init__.py)
2. **自動検出**: `src/commands/` 内のファイルが自動的にロードされます（`_*.py` ファイルを除く）
3. **各コマンドモジュール**は `setup(tree: app_commands.CommandTree)` 関数を持つ必要があります
4. **動的ロード**: `importlib` を使用したクリーンなモジュール管理

### 登録の仕組み

[src/commands/\_\_init\_\_.py](../src/commands/__init__.py):
```python
def register_commands(tree: app_commands.CommandTree):
    """自動的にコマンドを登録"""
    commands_dir = Path(__file__).parent

    for file_path in commands_dir.glob("*.py"):
        # _で始まるファイル（__init__.py, _sample.pyなど）を除外
        if file_path.stem.startswith("_"):
            continue

        # モジュールを動的にインポート
        module_name = f"src.commands.{file_path.stem}"
        module = importlib.import_module(module_name)

        # setup関数を呼び出してコマンドを登録
        if hasattr(module, "setup"):
            module.setup(tree)
```

### 新しいコマンドの追加

1. `src/commands/` に新しいファイルを作成（例: `my_command.py`）
2. `setup(tree)` 関数を実装
3. デコレーターパターンを使用（詳細は[ADD_COMMAND.md](./ADD_COMMAND.md)参照）
4. コマンドは自動的に `/help` と `/docs` に表示されます

**テンプレート**: [src/commands/\_sample.py](../src/commands/_sample.py)を起点として使用

### コマンドの同期

開発環境と本番環境で異なる同期戦略を使用:

**開発環境** (`.env.dev` with `DEV_GUILD_ID`):
```python
if dev_guild_id:
    # 即座に同期（開発モード）
    guild = discord.Object(id=int(dev_guild_id))
    tree.copy_global_to(guild=guild)
    synced = await tree.sync(guild=guild)
```

**本番環境** (`.env` without `DEV_GUILD_ID`):
```python
else:
    # グローバル同期（最大1時間かかる）
    synced = await tree.sync()
```

## 設定管理

### シングルトンパターン

[src/utils/event_config.py](../src/utils/event_config.py)で実装:

```python
class EventChannelConfig:
    """環境変数をキャッシュする設定クラス"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
```

**特徴**:
- 環境変数を一度だけ読み込み、キャッシュ
- 遅延ロード（初回アクセス時に検証）
- コードベース全体で一貫した設定アクセス

**使用例**:
```python
from src.utils.event_config import EventChannelConfig

config = EventChannelConfig()
category_name = config.event_category_name
```

## イベントチャンネルのインデックス管理

### インデックスフォーマット

イベントチャンネルは番号付きプレフィックスを使用: `{index}-{name}`

**例**:
- `1-hackathon`
- `2-study-group`
- `3-welcome-event`

### インデックス算出アルゴリズム

[src/utils/channel_utils.py](../src/utils/channel_utils.py)で実装:

```python
def get_next_event_index(guild: discord.Guild, config: EventChannelConfig) -> int:
    """次のイベントチャンネルのインデックスを取得"""
    # イベントカテゴリーとアーカイブカテゴリーの両方をスキャン
    # 正規表現 r"^(\d+)-" でインデックスを抽出
    # 最大値 + 1 を返す（最小値は1）
```

**重要なポイント**:
- **両方のカテゴリーをスキャン**: イベントとアーカイブの両方
- **正規表現**: `r"^(\d+)-"` を使用してインデックスを抽出
- **衝突回避**: アーカイブ/復元操作間で重複なし
- **最小値**: インデックスは1から始まる

**アルゴリズムの流れ**:
1. イベントカテゴリー内の全チャンネルを取得
2. アーカイブカテゴリー内の全チャンネルを取得
3. 各チャンネル名から `数字-` パターンを抽出
4. すべてのインデックスの最大値を取得
5. `max + 1` を返す（チャンネルがない場合は1）

これにより、以下のシナリオで正しく動作します:
- 新規チャンネル作成
- アーカイブ後の新規作成
- 復元後の新規作成
- 複数のアーカイブ/復元操作

## デプロイ構成

### Fly.io設定 ([fly.toml](../fly.toml))

- **リージョン**: Tokyo (NRT)
- **リソース**: 1GB RAM, 1 shared CPU
- **自動起動**: 有効
- **ヘルスチェック**: FastAPIサーバー経由のHTTP

### デプロイプロセス

1. `main` ブランチへのプッシュ
2. GitHub Actionsがデプロイワークフローをトリガー
3. Fly.ioがDockerイメージをビルド
4. 新しいインスタンスが東京リージョンにデプロイ
5. ヘルスチェックでデプロイメントを検証

## 関連ドキュメント

- [コマンド追加方法](./ADD_COMMAND.md) - 新しいコマンドの追加手順
- [ユーティリティ関数](./UTILITIES.md) - 共通ユーティリティの使い方
- [開発ガイド](./DEVELOPMENT.md) - 開発ワークフローとCI/CD
