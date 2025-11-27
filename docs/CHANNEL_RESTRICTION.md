# チャンネル制限デコレーター (@require_channel)

## 概要

`@require_channel` デコレーターは、特定のチャンネルでのみ（または特定のチャンネル以外で）コマンドを実行できるように制限する機能です。承認システム（`@require_approval`）と組み合わせることで、承認リクエスト送信前にチャンネル制限をチェックし、不正なチャンネルでの無駄な承認フローを防ぐことができます。

### 主な特徴

- **柔軟なチャンネル指定**: チャンネル名を直接指定、または環境変数から動的に取得
- **制限方向の制御**: 指定チャンネルでのみ実行 / 指定チャンネル以外で実行を選択可能
- **承認システムとの統合**: `@require_approval` より上位に配置することで早期バリデーションを実現
- **デコレーターベース**: コマンドに1行追加するだけで簡単に導入可能

## アーキテクチャ

### コンポーネント

| ファイル | 役割 |
|---------|------|
| [src/utils/channel_decorator.py](../src/utils/channel_decorator.py) | `@require_channel` デコレーター実装 |
| [src/utils/validation_utils.py](../src/utils/validation_utils.py) | `validate_channel_restriction()` ユーティリティ関数 |

### フロー図

```text
1. ユーザーがコマンド実行
   ↓
2. @require_channel デコレーターでチャンネル制限をチェック
   ├─ チャンネル不正 → エラーメッセージを表示して終了
   └─ チャンネル正常 → 次の処理へ（@require_approval など）
```

## 使い方

### 基本的な使い方

#### 1. チャンネル名を直接指定

```python
from discord import app_commands
import discord

from src.utils.command_metadata import command_meta
from src.utils.channel_decorator import require_channel

@command_meta(name="admin-command", description="管理コマンド")
@tree.command(name="admin-command", description="管理コマンドを実行します")
@require_channel(channel_name="管理チャンネル", must_be_in=True)
@app_commands.describe(action="実行するアクション")
async def admin_command_cmd(ctx: discord.Interaction, action: str):
    # このコマンドは「管理チャンネル」でのみ実行可能
    await ctx.response.send_message(f"アクション {action} を実行しました")
```

#### 2. 環境変数から動的に取得

```python
from src.utils.command_metadata import command_meta
from src.utils.channel_decorator import require_channel
from src.utils.approval_decorator import require_approval

@command_meta(name="create-event", description="イベント作成（承認必須）")
@tree.command(name="create-event", description="イベントを作成します")
@require_channel(channel_name_from_config="event_request_channel_name", must_be_in=True)
@require_approval(timeout_hours=24, description="新しいイベントを作成します")
@app_commands.describe(name="イベント名")
async def create_event_cmd(ctx: discord.Interaction, name: str):
    # このコマンドは EVENT_REQUEST_CHANNEL_NAME で指定されたチャンネルでのみ実行可能
    # かつ承認が必要
    await ctx.response.send_message(f"イベント {name} を作成しました")
```

#### 3. 指定チャンネル以外で実行

```python
@command_meta(name="general-chat", description="一般チャット")
@tree.command(name="general-chat", description="一般チャットコマンド")
@require_channel(channel_name="イベントリクエスト", must_be_in=False)
@app_commands.describe(message="メッセージ")
async def general_chat_cmd(ctx: discord.Interaction, message: str):
    # このコマンドは「イベントリクエスト」チャンネル以外で実行可能
    await ctx.response.send_message(f"メッセージ: {message}")
```

### デコレーターパラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `channel_name` | `str \| None` | `None` | チャンネル名を直接指定（`channel_name_from_config` と排他） |
| `channel_name_from_config` | `str \| None` | `None` | `ChannelConfig` の属性名を指定して動的取得（`channel_name` と排他） |
| `must_be_in` | `bool` | `True` | チャンネル制限の方向<br>- `True`: 指定チャンネルでのみ実行可能<br>- `False`: 指定チャンネル以外で実行可能 |

**重要**: `channel_name` と `channel_name_from_config` は排他的です。どちらか一方のみを指定してください。両方未指定または両方指定した場合は `ValueError` が発生します。

## 実装詳細

### デコレーターの動作

1. **パラメータ検証**: `channel_name` と `channel_name_from_config` の排他性をチェック
2. **チャンネル名の取得**:
   - `channel_name` が指定されている場合: その値を使用
   - `channel_name_from_config` が指定されている場合: `ChannelConfig` から動的に取得
3. **チャンネル制限チェック**: `validate_channel_restriction()` を呼び出し
4. **結果に応じた処理**:
   - チェック成功: 元の関数を実行
   - チェック失敗: エラーメッセージを表示して早期リターン（`validate_channel_restriction` 内でメッセージ送信済み）

### 環境変数からの動的取得

`channel_name_from_config` パラメータを使用すると、`ChannelConfig` の属性から動的にチャンネル名を取得できます。

**利用可能な属性**:
- `event_request_channel_name`: `EVENT_REQUEST_CHANNEL_NAME` 環境変数
- `event_category_name`: `EVENT_CATEGORY_NAME` 環境変数
- `archive_event_category_name`: `ARCHIVE_EVENT_CATEGORY_NAME` 環境変数

**メリット**:
- 環境ごとに異なるチャンネル名を使用できる（開発環境と本番環境で別のチャンネル）
- ハードコードを避け、設定を一元管理

### エラーハンドリング

#### パラメータエラー

```python
# ❌ 両方未指定
@require_channel()  # ValueError: channel_name または channel_name_from_config のいずれかを指定してください

# ❌ 両方指定
@require_channel(channel_name="管理", channel_name_from_config="event_request_channel_name")
# ValueError: channel_name と channel_name_from_config を同時に指定できません
```

#### 設定読み込みエラー

`channel_name_from_config` を使用した場合、以下のエラーが発生する可能性があります:

1. **`ChannelConfig.load()` 失敗**: 環境変数が設定されていない場合
   - デコレーター内で早期リターン（エラーメッセージは `ChannelConfig.load` 内で送信）
2. **属性が存在しない**: 指定した属性名が `ChannelConfig` に存在しない場合
   - エラーメッセージを送信して早期リターン

## 承認システムとの統合

### デコレーター順序（重要）

`@require_channel` は `@require_approval` より上位に配置してください。

```python
@command_meta(...)          # 1. 最上位
@tree.command(...)          # 2. コマンド登録
@require_channel(...)       # 3. チャンネル制限（承認より先）
@require_approval(...)      # 4. 承認ミドルウェア
@app_commands.describe(...) # 5. 引数説明
async def command_cmd(...):
    pass
```

**理由**:
- 承認リクエスト送信前にチャンネル制限をチェックできる
- 不正なチャンネルでの無駄な承認フローを防げる
- ユーザーに即座にエラーメッセージを表示できる

### 統合フロー

```text
1. ユーザーがコマンド実行
   ↓
2. @require_channel でチャンネルチェック
   ├─ チャンネル不正 → エラーメッセージを表示して終了
   └─ チャンネル正常 → 次へ
       ↓
3. @require_approval で権限チェック
   ├─ 承認ロール保持 → 即座に実行
   └─ 承認ロール未保持 → 承認リクエスト送信
       ↓
4. 承認者がボタンクリック
   ├─ 承認 → コマンド実行
   ├─ 拒否 → リクエスト者に通知
   └─ タイムアウト → 自動拒否
```

## 実装例

### イベントチャンネル作成コマンド

[src/commands/event_channel.py](../src/commands/event_channel.py) の `create_event_channel` コマンドで実際に使用されています:

```python
@command_meta(
    category="イベントチャンネル管理",
    icon="📅",
    short_description="イベント用のチャンネルとロールを作成",
    restrictions="• イベントリクエストチャンネルでのみ実行可能",
)
@tree.command(
    name="create_event_channel",
    description="新しいイベントチャンネルを作成します",
)
@require_channel(channel_name_from_config="event_request_channel_name", must_be_in=True)
@require_approval(timeout_hours=24, description="新しいイベントチャンネルを作成します")
@app_commands.describe(
    channel_name="作成するイベントチャンネル名",
    members="ロールに追加するメンバー（メンション形式で複数指定可能）",
)
async def create_event_channel(
    ctx: discord.Interaction,
    channel_name: str,
    members: str | None = None,
):
    await create_event_channel_impl(ctx, channel_name, members)
```

### フロー例

1. **ユーザーAが `/create_event_channel` コマンドを「一般チャンネル」で実行**
   - ユーザーAは承認ロール未保持
2. **`@require_channel` デコレーターでチャンネルチェック**
   - 「イベントリクエスト」チャンネルではないので失敗
   - エラーメッセージが表示: 「このコマンドは `イベントリクエスト` チャンネルでのみ実行できます」
   - **ここで終了**（承認リクエストは送信されない）

3. **ユーザーAが `/create_event_channel` コマンドを「イベントリクエスト」チャンネルで再実行**
   - `@require_channel` デコレーターでチャンネルチェック成功
   - `@require_approval` デコレーターで承認リクエスト送信
   - 承認者Bが承認ボタンをクリック
   - コマンド実行（イベントチャンネル作成）

## ベストプラクティス

### 1. チャンネル制限が必要なコマンド

以下のようなコマンドにはチャンネル制限を追加することを推奨します:

- **リクエスト系コマンド**: イベント作成リクエスト、チャンネル作成リクエストなど
- **管理系コマンド**: 管理チャンネルでのみ実行可能にする
- **カテゴリー固有の操作**: 特定のカテゴリー内でのみ実行可能にする

### 2. 環境変数の活用

チャンネル名をハードコードせず、環境変数から取得することを推奨します:

```python
# ✅ 推奨: 環境変数から取得
@require_channel(channel_name_from_config="event_request_channel_name", must_be_in=True)

# ❌ 非推奨: ハードコード
@require_channel(channel_name="イベントリクエスト", must_be_in=True)
```

**理由**:
- 環境ごとに異なるチャンネル名を使用できる
- 設定を一元管理できる
- チャンネル名の変更が容易

### 3. must_be_in の選択

- **`must_be_in=True`**: 特定のチャンネルでのみ実行可能にしたい場合
  - 例: イベント作成リクエストは「イベントリクエスト」チャンネルでのみ
- **`must_be_in=False`**: 特定のチャンネル以外で実行可能にしたい場合
  - 例: 一般的なコマンドは「管理チャンネル」以外で

### 4. ログの活用

チャンネル制限デコレーターは詳細なログを出力します:

- **チェック成功**: `DEBUG` レベル
- **チェック失敗**: `INFO` レベル
- **設定エラー**: `ERROR` レベル

トラブルシューティング時にログを確認してください。

## デコレーターを使わない場合

チャンネル制限のロジックが複雑な場合（引数に応じて制限が変わるなど）、デコレーターではなく実装関数内で直接 `validate_channel_restriction()` を呼び出すこともできます:

```python
from src.utils.validation_utils import validate_channel_restriction

async def complex_command_impl(ctx: discord.Interaction, option: str):
    config = await ChannelConfig.load(ctx)
    if not config:
        return

    # option に応じてチャンネル制限を変える
    if option == "admin":
        if not await validate_channel_restriction(ctx, "管理チャンネル", must_be_in=True):
            return
    elif option == "event":
        if not await validate_channel_restriction(ctx, config.event_request_channel_name, must_be_in=True):
            return

    # コマンドの処理
    ...
```

ただし、ほとんどの場合はデコレーターを使用する方がシンプルで推奨されます。

## トラブルシューティング

### チャンネル名が見つからない

**症状**: 「設定エラー: 環境変数 `xxx` が見つかりません」というエラーが表示される

**原因**: `channel_name_from_config` で指定した属性が `ChannelConfig` に存在しない

**解決方法**:
1. `ChannelConfig` の定義を確認（[src/utils/channel_config.py](../src/utils/channel_config.py)）
2. 利用可能な属性名を使用する
3. または `channel_name` パラメータで直接指定する

### 環境変数が設定されていない

**症状**: コマンド実行時にエラーメッセージが表示される

**原因**: 環境変数（`EVENT_REQUEST_CHANNEL_NAME` など）が `.env` ファイルに設定されていない

**解決方法**:
1. `.env` ファイルに必要な環境変数を追加
2. Botを再起動

### チャンネル制限が効かない

**症状**: どのチャンネルでもコマンドが実行できてしまう

**原因**:
1. デコレーターの順序が間違っている
2. チャンネル名のスペルミス

**解決方法**:
1. デコレーターの順序を確認（`@require_channel` は `@tree.command` の直後）
2. チャンネル名が正確か確認（大文字小文字も区別されます）

## 関連ドキュメント

- [APPROVAL.md](./APPROVAL.md) - 承認システムの仕様（`@require_approval` との統合）
- [ADD_COMMAND.md](./ADD_COMMAND.md) - コマンド追加手順（デコレーター順序）
- [UTILITIES.md](./UTILITIES.md) - ユーティリティ関数全般
- [ARCHITECTURE.md](./ARCHITECTURE.md) - アーキテクチャとパターン

## 参考: ファイル一覧

```text
src/
├── utils/
│   ├── channel_decorator.py      # @require_channel デコレーター
│   ├── validation_utils.py       # validate_channel_restriction()
│   └── channel_config.py            # ChannelConfig（環境変数管理）
└── commands/
    └── event_channel.py           # 実装例
```
