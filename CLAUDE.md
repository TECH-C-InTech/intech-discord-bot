# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**IMPORTANT: Always communicate in Japanese (日本語) when working in this repository.**

This is a Japanese development project, and all communication with users should be in Japanese unless explicitly requested otherwise.

## Quick Reference

### Development Commands

```bash
# Setup
uv sync --dev                    # Install dependencies (dev mode)
uv sync                          # Install dependencies (production)

# Run the bot
uv run bot.py                    # Production mode (uses .env)
uv run bot.py --env .env.dev     # Development mode (uses .env.dev, instant command sync)

# Code quality
uv run ruff format .             # Format code
uv run ruff format --check .     # Check formatting
uv run ruff check .              # Lint code
uv run ruff check --fix .        # Auto-fix lint issues
uv run mypy .                    # Type checking

# Deployment
fly deploy                       # Deploy to Fly.io
flyctl logs                      # View logs
flyctl status                    # Check deployment status
```

## Documentation Structure

**このリポジトリでは、詳細な実装情報やパターンは `docs/` ディレクトリに集約されています。**
**タスクを実行する際は、必ず該当するドキュメントを参照してください。**

### Core Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - アーキテクチャと設計パターン
  - 技術スタック
  - デュアルサーバーアーキテクチャ
  - 自動コマンド登録システム
  - 設定管理（シングルトンパターン）
  - イベントチャンネルのインデックス管理

- **[docs/ADD_COMMAND.md](docs/ADD_COMMAND.md)** - コマンド追加の手順
  - デコレーター順序（**必読**: `@command_meta` が最上位）
  - コマンド命名規則
  - メタデータシステム
  - テンプレートの使い方

- **[docs/UTILITIES.md](docs/UTILITIES.md)** - ユーティリティ関数
  - バリデーションユーティリティ
  - メッセージユーティリティ
  - チャンネルユーティリティ
  - ロギングパターン

- **[docs/APPROVAL.md](docs/APPROVAL.md)** - 承認システムの仕様
  - 承認フローの概要とアーキテクチャ
  - `@require_approval` デコレーターの使い方
  - スレッド連携とUI実装
  - 実装例とベストプラクティス

- **[docs/CHANNEL_RESTRICTION.md](docs/CHANNEL_RESTRICTION.md)** - チャンネル制限デコレーター
  - `@require_channel` デコレーターの概要
  - 基本的な使い方とパラメータ
  - 承認システムとの統合
  - 実装例とベストプラクティス

- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - 開発ワークフロー
  - 開発環境のセットアップ
  - コードスタイル規約
  - CI/CDパイプライン
  - デプロイ手順

- **[docs/SETUP.md](docs/SETUP.md)** - セットアップガイド
  - 環境変数の設定
  - Discord サーバーの設定
  - トラブルシューティング

- **[docs/INDEX.md](docs/INDEX.md)** - ドキュメントインデックス

## Critical Rules (詳細は docs/ を参照)

### 1. Decorator Ordering (MANDATORY)

**詳細**: [docs/ADD_COMMAND.md](docs/ADD_COMMAND.md)

コマンドは必ずこの順序でデコレーターを適用:

```python
@command_meta(...)  # ⚠️ 必ず最上位
@tree.command(...)
@app_commands.describe(...)
async def command_cmd(...):
    pass
```

### 2. Always Use docs/ for Implementation Details

- コマンド追加時 → [docs/ADD_COMMAND.md](docs/ADD_COMMAND.md)
- ユーティリティ使用時 → [docs/UTILITIES.md](docs/UTILITIES.md)
- アーキテクチャ理解 → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 開発環境構築 → [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- チャンネル制限追加時 → [docs/CHANNEL_RESTRICTION.md](docs/CHANNEL_RESTRICTION.md)
- 承認フロー追加時 → [docs/APPROVAL.md](docs/APPROVAL.md)

### 3. Development vs Production

**詳細**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#開発環境のセットアップ)

- **開発**: `.env.dev` with `DEV_GUILD_ID` (即座にコマンド同期)
- **本番**: `.env` without `DEV_GUILD_ID` (グローバル同期、最大1時間)

## Key Architectural Patterns

### Auto-Registration System

**詳細**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#コマンド登録システム)

- `src/commands/` 内のファイルが自動検出
- `setup(tree)` 関数で登録
- `_*.py` ファイルは除外

### Stateless Design

**詳細**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#アーキテクチャパターン)

- データベース不要
- すべての状態はDiscord上に存在
- 環境変数で設定を管理

## Important File Locations

### Core Files

- [bot.py](bot.py) - Main entry point, command sync logic
- [keep_alive.py](keep_alive.py) - FastAPI health check server
- [src/commands/\_\_init\_\_.py](src/commands/__init__.py) - Auto-registration system

### Templates & Examples

- [src/commands/\_sample.py](src/commands/_sample.py) - コマンドテンプレート

### Utilities

- [src/utils/command\_metadata.py](src/utils/command_metadata.py) - Metadata registry
- [src/utils/event\_config.py](src/utils/event_config.py) - Singleton config
- [src/utils/validation\_utils.py](src/utils/validation_utils.py) - Validation helpers
- [src/utils/message\_utils.py](src/utils/message_utils.py) - Message & error handling
- [src/utils/channel\_utils.py](src/utils/channel_utils.py) - Channel operations
- [src/utils/channel\_decorator.py](src/utils/channel_decorator.py) - Channel restriction decorator
- [src/utils/approval\_decorator.py](src/utils/approval_decorator.py) - Approval middleware
- [src/utils/approval\_utils.py](src/utils/approval_utils.py) - Approval utilities
- [src/views/approval\_view.py](src/views/approval_view.py) - Approval UI

## Workflow for Common Tasks

### Adding a New Command

1. Read [docs/ADD_COMMAND.md](docs/ADD_COMMAND.md)
2. Copy [src/commands/\_sample.py](src/commands/_sample.py)
3. Follow decorator ordering rules
4. Reference [docs/UTILITIES.md](docs/UTILITIES.md) for helper functions
5. (オプション) チャンネル制限が必要な場合は [docs/CHANNEL_RESTRICTION.md](docs/CHANNEL_RESTRICTION.md) を参照
6. (オプション) 承認が必要な場合は [docs/APPROVAL.md](docs/APPROVAL.md) を参照
7. Test with `.env.dev` and `DEV_GUILD_ID`

### Understanding Architecture

1. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
2. Review specific pattern sections as needed
3. Check related utility docs in [docs/UTILITIES.md](docs/UTILITIES.md)

### Setting Up Development Environment

1. Follow [docs/SETUP.md](docs/SETUP.md)
2. Configure dev environment per [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
3. Set up `DEV_GUILD_ID` for instant command sync

### Updating Documentation

**When making changes that affect architecture or utilities:**

1. Update the appropriate file in `docs/`:
   - Architecture changes → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
   - Utility changes → [docs/UTILITIES.md](docs/UTILITIES.md)
   - Command patterns → [docs/ADD_COMMAND.md](docs/ADD_COMMAND.md)
   - Channel restriction → [docs/CHANNEL_RESTRICTION.md](docs/CHANNEL_RESTRICTION.md)
   - Approval system → [docs/APPROVAL.md](docs/APPROVAL.md)
   - Workflow changes → [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

2. Update [docs/INDEX.md](docs/INDEX.md) if adding new sections

3. Keep CLAUDE.md as a high-level reference with pointers to docs/

## Testing Strategy

**詳細**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#テスト戦略)

- 現在、自動テストなし
- 環境分離によるマニュアルテスト
- 開発用と本番用で別々のBotトークンを使用
