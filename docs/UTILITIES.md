# ユーティリティ関数ガイド

このドキュメントでは、コードベース全体で使用される共通ユーティリティ関数について説明します。

## 📋 目次

1. [バリデーションユーティリティ](#バリデーションユーティリティ)
2. [メッセージユーティリティ](#メッセージユーティリティ)
3. [チャンネルユーティリティ](#チャンネルユーティリティ)
4. [コマンドメタデータ](#コマンドメタデータ)
5. [承認ミドルウェア](#承認ミドルウェア)
6. [設定管理](#設定管理)

## バリデーションユーティリティ

**場所**: [src/utils/validation_utils.py](../src/utils/validation_utils.py)

### `validate_channel_restriction(ctx, allowed_channel_name, must_be_in=True)`

特定のチャンネルでのみコマンド実行を許可するチェック。

**パラメータ**:
- `ctx: discord.Interaction` - Discord インタラクション
- `allowed_channel_name: str` - 許可するチャンネル名
- `must_be_in: bool` - `True`ならそのチャンネルのみ、`False`ならそのチャンネル以外（デフォルト: `True`）

**戻り値**:
- `bool` - バリデーション成功なら `True`、失敗なら `False`（エラーメッセージは自動送信）

**使用例**:
```python
from src.utils.validation_utils import validate_channel_restriction

async def my_command(ctx: discord.Interaction):
    if not await validate_channel_restriction(ctx, "event-request"):
        return  # エラーメッセージは既に送信されている

    # コマンドの処理
```

### `validate_channel_in_category(ctx, channel, category_name)`

チャンネルが指定されたカテゴリーに属しているかチェック。

**パラメータ**:
- `ctx: discord.Interaction` - Discord インタラクション
- `channel: discord.TextChannel` - チェックするチャンネル
- `category_name: str` - カテゴリー名

**戻り値**:
- `bool` - バリデーション成功なら `True`、失敗なら `False`（エラーメッセージは自動送信）

**使用例**:
```python
from src.utils.validation_utils import validate_channel_in_category

if not await validate_channel_in_category(ctx, channel, "event"):
    return  # エラーメッセージは既に送信されている
```

### `parse_member_mentions(ctx, members_str, guild)`

メンション文字列を解析して`discord.Member`オブジェクトのリストに変換。

**パラメータ**:
- `ctx: discord.Interaction` - Discord インタラクション
- `members_str: str` - メンション文字列（例: "@user1 @user2"）
- `guild: discord.Guild` - Discordギルド

**戻り値**:
- `list[discord.Member] | None` - メンバーオブジェクトのリスト。エラー時は `None`（エラーメッセージは自動送信）

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

### `validate_role_safety(ctx, role)`

ロールが安全に操作できるかチェック（管理者ロール、マネージドロール、@everyoneロールをブロック）。

**パラメータ**:
- `ctx: discord.Interaction` - Discord インタラクション
- `role: discord.Role` - チェックするロール

**戻り値**:
- `bool` - 安全なら `True`、危険なら `False`（エラーメッセージは自動送信）

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

### `get_next_event_index(guild, event_category_name, archive_event_category_name)`

次のイベントチャンネルのインデックスを取得。

**パラメータ**:
- `guild: discord.Guild` - Discordサーバー
- `event_category_name: str` - イベントカテゴリー名
- `archive_event_category_name: str` - アーカイブカテゴリー名

**戻り値**:
- `int` - 次のインデックス番号（最小値: 1）

**使用例**:
```python
from src.utils.channel_utils import get_next_event_index
from src.utils.channel_config import ChannelConfig

config = ChannelConfig.get_instance()
index = get_next_event_index(
    ctx.guild,
    config.event_category_name,
    config.archive_event_category_name
)
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
- `config: ChannelConfig` - 設定オブジェクト

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

## チャンネル制限デコレーター

**場所**: [src/utils/channel_decorator.py](../src/utils/channel_decorator.py)

### `@require_channel` デコレーター

特定のチャンネルでのみ（または特定のチャンネル以外で）コマンドを実行できるように制限するデコレーター。

**パラメータ**:
- `channel_name: str | None` - チャンネル名を直接指定（`channel_name_from_config` と排他）
- `channel_name_from_config: str | None` - `ChannelConfig` の属性名を指定して動的取得（`channel_name` と排他）
- `must_be_in: bool` - チャンネル制限の方向（デフォルト: `True`）
  - `True`: 指定チャンネルでのみ実行可能
  - `False`: 指定チャンネル以外で実行可能

**使用例（直接指定）**:
```python
from src.utils.channel_decorator import require_channel

@command_meta(...)
@tree.command(name="admin_command", description="管理コマンド")
@require_channel(channel_name="管理チャンネル", must_be_in=True)
@app_commands.describe(...)
async def admin_command_cmd(ctx: discord.Interaction, ...):
    # このコマンドは「管理チャンネル」でのみ実行可能
    await ctx.response.send_message("管理コマンドを実行しました")
```

**使用例（環境変数から取得）**:
```python
from src.utils.channel_decorator import require_channel

@command_meta(...)
@tree.command(name="create_event", description="イベント作成")
@require_channel(channel_name_from_config="event_request_channel_name", must_be_in=True)
@app_commands.describe(...)
async def create_event_cmd(ctx: discord.Interaction, ...):
    # このコマンドは EVENT_REQUEST_CHANNEL_NAME で指定されたチャンネルでのみ実行可能
    await ctx.response.send_message("イベントを作成しました")
```

**チャンネル制限と承認の組み合わせ**:
```python
@command_meta(...)
@tree.command(...)
@require_channel(channel_name_from_config="event_request_channel_name", must_be_in=True)
@require_approval(timeout_hours=24, description="新しいイベントを作成します")
@app_commands.describe(...)
async def create_event_cmd(ctx: discord.Interaction, ...):
    # 1. まずチャンネル制限をチェック
    # 2. 通過したら承認フローへ
    ...
```

**重要**: `@require_channel` は `@require_approval` より上位に配置してください。これにより、承認リクエスト送信前にチャンネル制限をチェックできます。

## 承認ミドルウェア

**場所**:
- [src/utils/approval_decorator.py](../src/utils/approval_decorator.py) - デコレーター
- [src/utils/approval_utils.py](../src/utils/approval_utils.py) - ユーティリティ関数
- [src/views/approval_view.py](../src/views/approval_view.py) - UI コンポーネント

### `@require_approval` デコレーター

特定のコマンドに承認フローを追加するデコレーター。Administrator権限を持つユーザーは承認不要で即座に実行され、それ以外のユーザーは承認リクエストを送信します。

**パラメータ**:
- `timeout_hours: int` - タイムアウト時間（時間単位）。デフォルトは24時間
- `description: str | None` - 承認リクエストに表示するコマンドの説明（任意）

**使用例**:
```python
from src.utils.approval_decorator import require_approval

@command_meta(
    category="イベント管理",
    icon="📅",
    short_description="新しいイベントチャンネルを作成",
)
@tree.command(name="create_event_channel", description="イベントチャンネルを作成")
@require_approval(timeout_hours=24, description="新しいイベントチャンネルを作成します")
@app_commands.describe(name="チャンネル名")
async def create_event_channel_cmd(ctx: discord.Interaction, name: str):
    # この関数は承認後に実行される
    await ctx.response.send_message(f"チャンネル {name} を作成しました")
```

**デコレーターの順序**:
```python
@command_meta(...)          # 最上位（必須）
@tree.command(...)          # Discord登録
@require_channel(...)       # チャンネル制限（オプション、承認より上位）
@require_approval(...)      # 承認ミドルウェア（ここに配置）
@app_commands.describe(...) # パラメータ説明
async def command(...):
```

### 承認フロー

1. **Administrator が実行した場合**:
   - 承認不要で即座にコマンドが実行される
   - ログに「Administrator」として記録

2. **一般ユーザーが実行した場合**:
   - 承認リクエストメッセージが送信される（Embed + ボタン）
   - Administratorが承認ボタンをクリックするとコマンド実行
   - Administratorが拒否ボタンをクリックすると拒否メッセージ表示
   - タイムアウト（デフォルト24時間）で自動的に拒否

### 承認ユーティリティ関数

承認リクエストや結果表示用のEmbed作成関数。

**使用可能な関数**:
```python
from src.utils.approval_utils import (
    create_approval_request_embed,
    create_approval_result_embed,
    create_rejection_result_embed,
    create_timeout_result_embed,
    has_administrator_permission,
)

# 承認リクエストEmbed
embed = create_approval_request_embed(
    command_name="/create_channel",
    requester=ctx.user,
    timeout_hours=24,
    description="新しいチャンネルを作成します"
)

# 承認成功Embed
embed = create_approval_result_embed("/create_channel", approver)

# 拒否Embed
embed = create_rejection_result_embed("/create_channel", rejector)

# タイムアウトEmbed
embed = create_timeout_result_embed("/create_channel", 24)

# Administrator権限チェック
if has_administrator_permission(member):
    # 即座に実行
```

### ApprovalView クラス

承認/拒否ボタンを持つUIコンポーネント。通常はデコレーター経由で自動的に使用されます。

**ボタン**:
- ✅ **承認ボタン（緑）**: Administrator権限を持つユーザーがクリックするとコマンド実行
- ❌ **拒否ボタン（赤）**: Administrator権限を持つユーザーがクリックすると拒否

**タイムアウト処理**:
- 指定時間（デフォルト24時間）経過すると自動的に拒否
- メッセージを編集してタイムアウトを表示
- ボタンを無効化

### 注意事項

**Interactionコンテキストの扱い**:
- 承認後に実行されるコマンドには、承認ボタンの`Interaction`が渡されます
- 元の`ctx.response`は承認リクエスト送信時に既に使用済みです
- コマンド内では`ctx.response.send_message()`または`ctx.followup.send()`が使用できます

**Bot再起動時の動作**:
- 24時間のタイムアウト中にBotが再起動すると、承認リクエストは未処理のまま残ります
- ユーザーがボタンをクリックすると「このインタラクションは無効です」とDiscordが表示します
- この動作は現時点では許容範囲として設計されています

**ログ記録**:
```python
# 承認リクエスト送信時
logger.info(f"Approval request sent for command '{command_name}' by {user}")

# 承認時
logger.info(f"Command '{command_name}' approved by {approver}")

# 拒否時
logger.warning(f"Command '{command_name}' rejected by {rejector}")

# タイムアウト時
logger.warning(f"Approval request for '{command_name}' timed out")
```

### 将来的な拡張

現在は「一人でも承認すればOK」モードのみ実装されています。将来的には以下の拡張が考えられます：

- **全員承認モード**: 複数のAdministratorが全員承認する必要があるモード
- **拒否理由の入力**: Modalを使用して拒否理由を記述する機能
- **承認履歴の記録**: データベースやログファイルに承認履歴を保存
- **Bot再起動後の復元**: 未処理の承認リクエストを復元する機能

## 設定管理

**場所**: [src/utils/channel_config.py](../src/utils/channel_config.py)

### `ChannelConfig` クラス

環境変数を管理するシングルトンクラス。

**使用例**:
```python
from src.utils.channel_config import ChannelConfig

config = ChannelConfig.get_instance()

# 設定値へのアクセス
event_category = config.event_category_name
archive_category = config.archive_event_category_name
request_channel = config.event_request_channel_name
club_category = config.club_category_name
```

**プロパティ**:
- `event_category_name: str` - イベントカテゴリー名
- `archive_event_category_name: str` - アーカイブカテゴリー名
- `event_request_channel_name: str` - リクエストチャンネル名
- `club_category_name: str` - クラブカテゴリー名
- `clubs_request_channel_name: str` - クラブ作成リクエストチャンネル名

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
