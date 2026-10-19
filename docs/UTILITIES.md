# ユーティリティ関数ガイド

このドキュメントでは、コードベース全体で使用される共通ユーティリティ関数について説明します。

## 📋 目次

1. [バリデーションユーティリティ](#バリデーションユーティリティ)
2. [メッセージユーティリティ](#メッセージユーティリティ)
3. [チャンネルユーティリティ](#チャンネルユーティリティ)
4. [作成と上限チェック](#作成と上限チェック)
5. [記録](#記録)
6. [コマンドメタデータ](#コマンドメタデータ)
7. [設定管理](#設定管理)

## バリデーションユーティリティ

**場所**: [src/utils/validation_utils.py](../src/utils/validation_utils.py)

### `validate_channel_in_category(ctx, channel, category_name)`

チャンネルが指定されたカテゴリーに属しているかチェック。

**パラメータ**:
- `ctx: discord.Interaction` - Discord インタラクション
- `channel: discord.TextChannel` - チェックするチャンネル
- `category_name: str` - カテゴリー名

**戻り値**:
- `bool` - チャンネルがカテゴリーに属しているか

**使用例**:
```python
from src.utils.validation_utils import validate_channel_in_category

valid = await validate_channel_in_category(ctx, ctx.channel, "event")
if not valid:
    # エラーメッセージは自動表示
    return
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
    member_list = await parse_member_mentions(ctx, members, ctx.guild)
    if member_list is None:
        return  # エラーメッセージは既に送信されている

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
    if not await validate_role_safety(ctx, role):
        return  # エラーメッセージは既に送信されている

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

### `send_private_reply(ctx, embed)`

操作した本人にだけ見える返信を送る。defer済みの前提で`followup`を使い、毎回`ephemeral=True`を指定する（2通目以降のfollowupはdeferの可視性を引き継がないため）。followupに失敗したら、deferで出た「考え中…」の応答を結果で書き換える。それにも失敗しても例外は出さない。

```python
await ctx.response.defer(ephemeral=True, thinking=True)
# ... 操作 ...
await send_private_reply(ctx, create_success_embed(title="作成完了", description="..."))
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

config = await ChannelConfig.load(ctx)
index = get_next_event_index(ctx.guild, config.event_category_name, config.archive_event_category_name)
channel_name = f"e{index:03d}-{event_name}"
```

**アルゴリズム**:
1. イベントカテゴリーとアーカイブカテゴリーの両方をスキャン
2. 正規表現 `r"^e(\d{3})-"` でインデックスを抽出（3桁0埋め）
3. 最大値 + 1 を返す（最小値は1）
4. アーカイブ/復元操作間で衝突を回避

詳細は [ARCHITECTURE.md](./ARCHITECTURE.md#イベントチャンネルのインデックス管理) を参照。

### `resolve_target_text_channel(channel)`

コマンドが実行された場所（`Interaction.channel`）から、対象にするテキストチャンネルを決める。

**戻り値**:
- `tuple[discord.TextChannel | None, bool]` - (対象のチャンネル, スレッドの親を対象にしたか)

| 実行された場所 | 戻り値 |
|---|---|
| テキストチャンネル | (そのチャンネル, `False`) |
| テキストチャンネルのスレッド | (親チャンネル, `True`) |
| フォーラムのスレッド、ボイスチャンネルなど | (`None`, `False`) |

スレッドの親を対象にした場合は、そのことを本人への返信で伝える。

コマンドからは、決められなければ本人にエラーを返す`resolve_target_text_channel_or_error(ctx)`と、返信に添える一文を作る`thread_target_note(channel, via_thread)`を使う。

### `find_event_channel_by_name(guild, partial_name, category_name)`

部分一致でイベントチャンネルを検索。

**パラメータ**:
- `guild: discord.Guild` - Discordサーバー
- `partial_name: str` - チャンネル名（部分一致）
- `category_name: str` - カテゴリー名

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
- `e001-hackathon` というチャンネル名に対して `"hackathon"` で検索可能
- インデックス部分（`e001-`）を除いた名前で部分一致
- 大文字小文字を区別

## 作成と上限チェック

### `create_channel_with_role(guild, category, *, decide_name, role_name_for, role_kind=None, lock=creation_lock)`

**場所**: [src/utils/creation.py](../src/utils/creation.py)

上限チェックから、チャンネルとロールの作成までをサーバー全体で1つのLockの中で行う。ロールの作成に失敗したらチャンネルを削除して元に戻す。

**パラメータ**:
- `decide_name(guild, category) -> str | Rejected` - チャンネル名を決める（採番）
- `role_name_for(channel) -> str` - 作成されたチャンネルからロール名を決める
- `role_kind` - `club` / `event` / `project`。指定すると、作成したロールを同じ種類のロールの並びへ動かす

**戻り値**:
- `Created(channel, role)` - 作成できた
- `Rejected(reason)` - 上限などで拒否した（何も残らない）
- `Failed(error, leftover_channel)` - Discordの操作に失敗した。ロールバックできなかったチャンネルがあれば`leftover_channel`に入る

`Rejected`と`Failed`は`report_creation_problem(ctx, outcome, action)`（[src/utils/message_utils.py](../src/utils/message_utils.py)）で本人に返す。ロールバックできなかったチャンネルがあれば、管理者への削除依頼もあわせて伝える。設計は [ARCHITECTURE.md](./ARCHITECTURE.md#作成の直列化と上限チェック) を参照。

### `check_creation_capacity(...)` / `check_move_capacity(...)`

**場所**: [src/utils/capacity.py](../src/utils/capacity.py)

件数だけを受け取り、上限に達していれば理由を、余裕があれば`None`を返す純粋関数。`remaining_capacity(...)`は上限までの残り件数を返す。

```python
reason = check_move_capacity(destination_category_channels=len(archive_category.channels))
if reason is not None:
    await send_error_message(ctx, reason)
    return
```

### `next_number(prefix, names)` / `number_of(prefix, name)`

**場所**: [src/utils/numbering.py](../src/utils/numbering.py)

番号の採番と読み取り。`next_number("c", names)`は、`cNNN-`で始まる名前の最大の番号に1を足す（欠番は埋めない）。`number_of("c", "c005-ラーメン")`は`5`を返し、番号がなければ`None`を返す。

### `sort_category(guild, *, category_id, prefix)` / `sorted_channel_positions(prefix, channels)`

**場所**: [src/utils/channel_order.py](../src/utils/channel_order.py)

カテゴリ内のテキストチャンネルを番号順に並べ直す。`sorted_channel_positions`は (ID, 名前, 位置) から変わる位置だけを返す純粋関数。並べ方は [ARCHITECTURE.md](./ARCHITECTURE.md#チャンネルの並び) を参照。

### `target_role_position(kind, roles)`

**場所**: [src/utils/role_order.py](../src/utils/role_order.py)

作成したロールを動かす先の位置を返す純粋関数。`roles`は作成したロール以外の`(名前, 位置)`。並べ方は [ARCHITECTURE.md](./ARCHITECTURE.md#ロールの並び) を参照。

### `grant_role(members, role)`

**場所**: [src/utils/role_utils.py](../src/utils/role_utils.py)

メンバーにロールを付与し、`GrantResult(granted, already_had, failed)`を返す。失敗した人がいても残りの人への付与は続ける。

`with_creator(members, creator)`は作成者を先頭に加えた参加者の一覧を返す（重複は除く）。作成コマンドはこれを`grant_role`に渡し、立てた本人も参加者にする。

`describe_grant(result)`は結果を本人への返信用の説明文にする。付与できなかった人がいれば、botのロールの順位と「ロールの管理」権限を確かめる案内も添える。メンバー追加で誰にも付与できなかった場合は、成功ではなくエラーとして返す。

## 記録

**場所**: [src/utils/records.py](../src/utils/records.py)

どこに何を残すかは [ARCHITECTURE.md](./ARCHITECTURE.md#記録の出し先) を参照。

### 組み立て

- `build_creation_embed(...)` - 作成（ログ・チャンネル内で共通。参加方法の項目つき）
- `build_members_added_embed(...)` - メンバー追加（チャンネル内）
- `build_archive_notice_embed(...)` - アーカイブ（チャンネル内、移動の前に投稿）
- `build_restored_embed(...)` - 復元（チャンネル内、移動の後）

### 送信

- `post_channel_record(channel, embed, mention_users=())` - 対象チャンネルへ送る。`mention_users`だけを本文のメンションで通知する。送信したメッセージ（送れなければ`None`）を返す

送信に失敗しても例外は出さず、warningを出す。

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
    restrictions="• どのチャンネル・スレッドからでも実行可能",
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

**場所**: [src/utils/channel_config.py](../src/utils/channel_config.py)

### `ChannelConfig` クラス

環境変数を管理する非同期設定クラス。

**使用例**:
```python
from src.utils.channel_config import ChannelConfig

config = await ChannelConfig.load(ctx)

# 設定値へのアクセス
event_category = config.event_category_name
archive_category = config.archive_event_category_name
project_category = config.project_category_name
club_category = config.club_category_name
```

**プロパティ** (主要):
- `event_category_name: str` - イベントカテゴリー名
- `archive_event_category_name: str` - アーカイブカテゴリー名
- `project_category_name: str` - プロジェクトカテゴリー名
- `archive_project_category_name: str` - プロジェクトアーカイブカテゴリー名
- `club_category_name: str` - クラブカテゴリー名

**特徴**:
- 非同期ロード (`await ChannelConfig.load(ctx)`)
- 初回アクセス時に環境変数を読み込み、キャッシュ
- バリデーション付き（すべて必須）
- エラーメッセージは自動表示（不足している環境変数だけを並べる）

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
