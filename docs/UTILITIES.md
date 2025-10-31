# ユーティリティ関数ガイド

このドキュメントでは、コードベース全体で使用される共通ユーティリティ関数について説明します。

## 📋 目次

1. [バリデーションユーティリティ](#バリデーションユーティリティ)
2. [メッセージユーティリティ](#メッセージユーティリティ)
3. [チャンネルユーティリティ](#チャンネルユーティリティ)
4. [コマンドメタデータ](#コマンドメタデータ)
5. [設定管理](#設定管理)

## バリデーションユーティリティ

**場所**: [src/utils/validation_utils.py](../src/utils/validation_utils.py)

### `validate_channel_restriction(ctx, channel_name)`

特定のチャンネルでのみコマンド実行を許可するチェック。

**パラメータ**:
- `ctx: discord.Interaction` - Discord インタラクション
- `channel_name: str` - 許可するチャンネル名

**戻り値**:
- `str | None` - エラーメッセージ（制限違反の場合）、または `None`（OK の場合）

**使用例**:
```python
from src.utils.validation_utils import validate_channel_restriction

async def my_command(ctx: discord.Interaction):
    error = validate_channel_restriction(ctx, "event-request")
    if error:
        await send_error_message(ctx, error)
        return

    # コマンドの処理
```

### `validate_channel_in_category(channel, category_name, config)`

チャンネルが指定されたカテゴリーに属しているかチェック。

**パラメータ**:
- `channel: discord.TextChannel` - チェックするチャンネル
- `category_name: str` - カテゴリー名（"event" または "archive"）
- `config: EventChannelConfig` - 設定オブジェクト

**戻り値**:
- `str | None` - エラーメッセージ、または `None`

**使用例**:
```python
from src.utils.validation_utils import validate_channel_in_category
from src.utils.event_config import EventChannelConfig

config = EventChannelConfig()
error = validate_channel_in_category(channel, "event", config)
if error:
    await send_error_message(ctx, error)
    return
```

### `parse_member_mentions(ctx, mention_string)`

メンション文字列を解析して`discord.Member`オブジェクトのリストに変換。

**パラメータ**:
- `ctx: discord.Interaction` - Discord インタラクション
- `mention_string: str | None` - メンション文字列（例: "@user1 @user2"）

**戻り値**:
- `list[discord.Member]` - メンバーオブジェクトのリスト

**使用例**:
```python
from src.utils.validation_utils import parse_member_mentions

async def add_members_command(ctx: discord.Interaction, members: str):
    member_list = parse_member_mentions(ctx, members)

    if not member_list:
        await send_error_message(ctx, "有効なメンバーが見つかりませんでした")
        return

    # メンバーリストを処理
    for member in member_list:
        # 処理...
```

**サポートされる形式**:
- `@username` - メンション形式
- `<@123456789>` - ID形式のメンション
- 複数メンションをスペース区切り

### `validate_role_safety(role)`

ロールが安全に操作できるかチェック（管理者ロール、マネージドロール、@everyoneロールをブロック）。

**パラメータ**:
- `role: discord.Role` - チェックするロール

**戻り値**:
- `str | None` - エラーメッセージ、または `None`

**使用例**:
```python
from src.utils.validation_utils import validate_role_safety

async def modify_role_command(ctx: discord.Interaction, role: discord.Role):
    error = validate_role_safety(role)
    if error:
        await send_error_message(ctx, error)
        return

    # ロールの操作
```

**ブロックされるロール**:
- 管理者権限を持つロール
- Bot/インテグレーションのマネージドロール
- @everyone ロール

## メッセージユーティリティ

**場所**: [src/utils/message_utils.py](../src/utils/message_utils.py)

### `send_error_message(ctx, message, help_text=None)`

ユーザーフレンドリーなエラーメッセージを送信。

**パラメータ**:
- `ctx: discord.Interaction` - Discord インタラクション
- `message: str` - エラーメッセージ
- `help_text: str | None` - 追加のヘルプテキスト（任意）

**使用例**:
```python
from src.utils.message_utils import send_error_message

await send_error_message(
    ctx,
    "チャンネルの作成に失敗しました",
    help_text="チャンネル名は50文字以内で指定してください"
)
```

### `handle_command_error(ctx, error, operation_name)`

Discord APIエラーを一貫した方法で処理。

**パラメータ**:
- `ctx: discord.Interaction` - Discord インタラクション
- `error: Exception` - 発生したエラー
- `operation_name: str` - 操作の説明

**使用例**:
```python
from src.utils.message_utils import handle_command_error

try:
    await channel.delete()
except discord.Forbidden as e:
    await handle_command_error(ctx, e, "チャンネルの削除")
except discord.HTTPException as e:
    await handle_command_error(ctx, e, "チャンネルの削除")
```

**自動処理されるエラー**:
- `discord.Forbidden` - 権限不足
- `discord.HTTPException` - Discord API エラー
- その他の例外 - 一般的なエラーメッセージ

### `create_success_embed(message)`

成功メッセージ用のEmbedを作成。

**パラメータ**:
- `message: str` - 成功メッセージ

**戻り値**:
- `discord.Embed` - 成功メッセージのEmbed（緑色）

**使用例**:
```python
from src.utils.message_utils import create_success_embed

embed = create_success_embed("チャンネルを作成しました")
await ctx.response.send_message(embed=embed)
```

### Interactionレスポンスパターン

**重要**: 必ずレスポンスの状態をチェックしてから送信してください。

```python
# 正しいパターン
if not ctx.response.is_done():
    await ctx.response.send_message(...)
else:
    await ctx.followup.send(...)
```

**理由**:
- `ctx.response.send_message()` は一度しか呼べない
- 既にレスポンス済みの場合は `ctx.followup.send()` を使用
- チェックしないとエラーが発生する

## チャンネルユーティリティ

**場所**: [src/utils/channel_utils.py](../src/utils/channel_utils.py)

### `get_next_event_index(guild, config)`

次のイベントチャンネルのインデックスを取得。

**パラメータ**:
- `guild: discord.Guild` - Discordサーバー
- `config: EventChannelConfig` - 設定オブジェクト

**戻り値**:
- `int` - 次のインデックス番号（最小値: 1）

**使用例**:
```python
from src.utils.channel_utils import get_next_event_index
from src.utils.event_config import EventChannelConfig

config = EventChannelConfig()
index = get_next_event_index(ctx.guild, config)
channel_name = f"{index}-{event_name}"
```

**アルゴリズム**:
1. イベントカテゴリーとアーカイブカテゴリーの両方をスキャン
2. 正規表現 `r"^(\d+)-"` でインデックスを抽出
3. 最大値 + 1 を返す（最小値は1）
4. アーカイブ/復元操作間で衝突を回避

詳細は [ARCHITECTURE.md](./ARCHITECTURE.md#イベントチャンネルのインデックス管理) を参照。

### `find_event_channel_by_name(guild, partial_name, config)`

部分一致でイベントチャンネルを検索。

**パラメータ**:
- `guild: discord.Guild` - Discordサーバー
- `partial_name: str` - チャンネル名（部分一致）
- `config: EventChannelConfig` - 設定オブジェクト

**戻り値**:
- `discord.TextChannel | None` - 見つかったチャンネル、または `None`

**使用例**:
```python
from src.utils.channel_utils import find_event_channel_by_name

channel = find_event_channel_by_name(ctx.guild, "hackathon", config)
if not channel:
    await send_error_message(ctx, "チャンネルが見つかりませんでした")
    return
```

**検索の挙動**:
- `1-hackathon` というチャンネル名に対して `"hackathon"` で検索可能
- インデックス部分（`1-`）を除いた名前で部分一致
- 大文字小文字を区別

## コマンドメタデータ

**場所**: [src/utils/command_metadata.py](../src/utils/command_metadata.py)

### `@command_meta` デコレーター

コマンドのメタデータを登録し、`/help`と`/docs`で自動表示。

**パラメータ**:
- `category: str` - カテゴリー名（必須）
- `icon: str` - カテゴリーアイコン（絵文字、必須）
- `short_description: str` - 短い説明（推奨）
- `restrictions: str | None` - 実行制限の説明（任意）
- `examples: list[str]` - 使用例のリスト（推奨）
- `notes: str | None` - 追加の注意事項（任意）

**使用例**:
```python
from src.utils.command_metadata import command_meta

@command_meta(
    category="イベント管理",
    icon="📅",
    short_description="新しいイベントチャンネルを作成",
    restrictions="event-requestチャンネルでのみ実行可能",
    examples=[
        "`/create_event_channel name:ハッカソン`",
        "`/create_event_channel name:勉強会 members:@user1 @user2`",
    ],
    notes="チャンネル名は50文字以内で指定してください",
)
@tree.command(name="create_event_channel", description="イベントチャンネルを作成")
async def create_event_channel_cmd(ctx: discord.Interaction, name: str, members: str = None):
    # コマンドの実装
```

**重要**: `@command_meta` は必ず最上位のデコレーターとして配置してください。詳細は [ADD_COMMAND.md](./ADD_COMMAND.md#デコレーターの順序重要) を参照。

## 設定管理

**場所**: [src/utils/event_config.py](../src/utils/event_config.py)

### `EventChannelConfig` クラス

環境変数を管理するシングルトンクラス。

**使用例**:
```python
from src.utils.event_config import EventChannelConfig

config = EventChannelConfig()

# 設定値へのアクセス
event_category = config.event_category_name
archive_category = config.archive_event_category_name
request_channel = config.event_request_channel_name
```

**プロパティ**:
- `event_category_name: str` - イベントカテゴリー名
- `archive_event_category_name: str` - アーカイブカテゴリー名
- `event_request_channel_name: str` - リクエストチャンネル名

**特徴**:
- シングルトンパターン（インスタンスは1つのみ）
- 初回アクセス時に環境変数を読み込み、キャッシュ
- バリデーション付き

詳細は [ARCHITECTURE.md](./ARCHITECTURE.md#設定管理) を参照。

## ロギングパターン

すべてのモジュールで一貫したロギングパターンを使用してください。

```python
from logging import getLogger

logger = getLogger(__name__)

# 情報ログ
logger.info(f"チャンネルを作成しました: {channel.name}")

# エラーログ（スタックトレース付き）
logger.error(f"チャンネルの作成に失敗しました: {error}", exc_info=True)

# デバッグログ
logger.debug(f"処理中のユーザー: {user.name}")
```

**ログレベル**:
- `DEBUG` - 詳細なデバッグ情報
- `INFO` - 一般的な情報（操作の成功など）
- `WARNING` - 警告（処理は続行）
- `ERROR` - エラー（処理は失敗）

## 関連ドキュメント

- [コマンド追加方法](./ADD_COMMAND.md) - 新しいコマンドの追加手順
- [アーキテクチャガイド](./ARCHITECTURE.md) - システムアーキテクチャの詳細
- [開発ガイド](./DEVELOPMENT.md) - 開発ワークフローとCI/CD
