# 承認システム (Approval System)

## 概要

承認システムは、特定のコマンドに対して事前承認フローを追加する機能です。承認権限を持つユーザーが即座に実行できる一方で、権限のないユーザーは承認リクエストを送信し、承認者による承認を待つ必要があります。

### 主な特徴

- **ロールベースの権限管理**: 環境変数で設定した承認ロールを持つユーザーが承認・拒否を実行可能
- **スレッドベースのUI**: 承認リクエストごとにスレッドが作成され、詳細やコマンド実行結果がスレッド内に表示
- **タイムアウト機能**: 指定時間内に承認されない場合、自動的に拒否される
- **デコレーターベース**: `@require_approval` デコレーターを追加するだけで簡単に承認フローを導入可能

## アーキテクチャ

### コンポーネント構成

承認システムは以下の4つのコンポーネントで構成されています:

| ファイル | 役割 |
|---------|------|
| [src/utils/approval_config.py](../src/utils/approval_config.py) | 承認システムの設定管理（シングルトンパターン） |
| [src/utils/approval_decorator.py](../src/utils/approval_decorator.py) | `@require_approval` デコレーター実装 |
| [src/utils/approval_utils.py](../src/utils/approval_utils.py) | Embed作成、権限チェックなどのユーティリティ関数 |
| [src/views/approval_view.py](../src/views/approval_view.py) | 承認/拒否ボタンを持つUI（View）とスレッド連携 |

### フロー図

```text
1. ユーザーがコマンド実行
   ↓
2. @require_approval デコレーターが権限チェック
   ├─ 承認ロール保持 → 即座に実行
   └─ 承認ロール未保持 → 承認リクエスト送信
       ↓
3. 承認リクエストメッセージ + スレッド作成
   ├─ メインチャンネル: 承認/拒否ボタン + Embed
   └─ スレッド内: リクエスト詳細 + コマンド実行結果
       ↓
4. 承認者がボタンクリック
   ├─ 承認 → コマンド実行（結果はスレッド内）
   ├─ 拒否 → リクエスト者に通知
   └─ タイムアウト → 自動拒否
```

## 使い方

### 1. 環境変数の設定

`.env` または `.env.dev` に承認ロール名を設定します:

```bash
# 承認権限を持つロール名（デフォルト: "Administrator"）
APPROVER_ROLE_NAME=運営
```

未設定の場合、デフォルトで `"Administrator"` ロールが使用されます。

### 2. コマンドへのデコレーター追加

承認フローを追加したいコマンドに `@require_approval` デコレーターを追加します。

**重要**: デコレーターの順序を守ってください（[docs/ADD_COMMAND.md](./ADD_COMMAND.md) 参照）。

```python
from discord import app_commands
import discord

from src.utils.command_metadata import command_meta
from src.utils.approval_decorator import require_approval

@command_meta(name="delete-channel", description="チャンネル削除（承認必須）")
@tree.command(name="delete-channel", description="チャンネルを削除します")
@require_approval(timeout_hours=24, description="チャンネルを完全に削除します")
@app_commands.describe(channel="削除するチャンネル")
async def delete_channel_cmd(
    ctx: discord.Interaction,
    channel: discord.TextChannel
):
    await channel.delete()
    await ctx.response.send_message(f"チャンネル {channel.name} を削除しました")
```

### 3. デコレーターパラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `timeout_hours` | `int` | `24` | タイムアウト時間（時間単位） |
| `description` | `str \| None` | `None` | 承認リクエストに表示する説明文 |

## 実装詳細

### 1. 権限チェック (`approval_decorator.py`)

コマンド実行時、デコレーター内で以下のチェックを実行:

1. **ギルド内実行チェック**: DMでは使用不可
2. **承認ロール保持チェック**:
   - ロール保持 → `command_func` を即座に実行
   - ロール未保持 → 承認リクエストフローへ

```python
# has_approver_role() で権限チェック
if has_approver_role(interaction.user):
    # 承認ロール保持者は即座に実行
    return await func(interaction, *args, **kwargs)
```

### 2. 承認リクエストの送信 (`approval_decorator.py`)

承認リクエストは以下の手順で送信されます:

1. **Embedとボタン作成**:
   - `create_approval_request_embed()` で承認リクエストEmbedを作成
   - `ApprovalView` で承認/拒否ボタンを作成
2. **ロールメンション**:
   - 承認ロールを持つロールIDを取得してメンション
3. **メッセージ送信**:
   - `interaction.response.send_message()` または `interaction.followup.send()`
4. **スレッド作成**:
   - 送信したメッセージに対してスレッドを作成
   - スレッド内にリクエスト詳細（`create_request_details_embed()`）を投稿

```python
# スレッド作成とリクエスト詳細投稿
thread = await message.create_thread(
    name=f"承認: {command_name}",
    auto_archive_duration=1440,  # 24時間
)
details_embed = create_request_details_embed(...)
await thread.send(embed=details_embed)
```

### 3. 承認/拒否処理 (`approval_view.py`)

`ApprovalView` クラスは `discord.ui.View` を継承し、承認/拒否ボタンを実装しています。

#### 承認ボタン (`approve_button`)

1. **権限チェック**: `has_approver_role()` で承認権限を確認
2. **ボタン無効化**: すべてのボタンを無効化
3. **メッセージ編集**: 承認結果Embedに更新
4. **スレッド通知**: スレッド内に承認通知を投稿
5. **コマンド実行**: `ThreadBoundInteraction` でコマンドを実行
   - コマンドの出力はすべてスレッド内に送信される

```python
# スレッドへ束縛されたInteractionを作成
interaction_for_command = ThreadBoundInteraction(self.original_interaction, self.thread)

# コマンド実行（出力はスレッド内）
await self.command_func(interaction_for_command, *self.args, **self.kwargs)
```

#### 拒否ボタン (`reject_button`)

1. **権限チェック**: `has_approver_role()` で拒否権限を確認
2. **ボタン無効化**: すべてのボタンを無効化
3. **メッセージ編集**: 拒否結果Embedに更新
4. **スレッド通知**: スレッド内に拒否通知を投稿
5. **リクエスト者通知**: スレッド内にリクエスト者をメンションして拒否を通知

#### タイムアウト処理 (`on_timeout`)

タイムアウト時間（デフォルト24時間）が経過すると:

1. **ボタン無効化**: すべてのボタンを無効化
2. **メッセージ編集**: タイムアウト結果Embedに更新

### 4. スレッド連携 (`approval_view.py`)

承認後のコマンド実行結果をスレッド内に表示するため、`ThreadBoundInteraction` を実装しています。

#### `ThreadBoundInteraction`

元の `discord.Interaction` をラップし、`response` と `followup` をスレッドに向けます:

- **`ThreadBoundResponse`**: `send_message()` をスレッドの `send()` にリダイレクト
- **`ThreadBoundFollowup`**: `send()` をスレッドの `send()` にリダイレクト

```python
class ThreadBoundInteraction:
    def __init__(self, original_interaction, thread):
        self._original_interaction = original_interaction
        self._thread = thread
        self.response = ThreadBoundResponse(original_interaction.response, thread)
        self.followup = ThreadBoundFollowup(thread)
```

これにより、コマンド内の `ctx.response.send_message()` や `ctx.followup.send()` がすべてスレッド内に送信されます。

### 5. Embed作成 (`approval_utils.py`)

以下のユーティリティ関数でEmbedを作成:

| 関数名 | 用途 | 色 |
|-------|------|-----|
| `create_approval_request_embed()` | 承認リクエスト | 青 (Blue) |
| `create_request_details_embed()` | リクエスト詳細（スレッド内） | 青 (Blue) |
| `create_approval_result_embed()` | 承認完了 | 緑 (Green) |
| `create_rejection_result_embed()` | 拒否 | 赤 (Red) |
| `create_timeout_result_embed()` | タイムアウト | オレンジ (Orange) |

すべてのEmbedにはタイムスタンプ（`datetime.now(timezone.utc)`）が付与されます。

## 実装例

### イベントチャンネル作成コマンド

[src/commands/event_channel.py](../src/commands/event_channel.py) の `create_event_channel_cmd` で実際に使用されています:

```python
@command_meta(
    name="event",
    description="イベントチャンネル作成（承認必須）",
)
@tree.command(
    name="event",
    description="イベントチャンネルを作成します",
)
@require_approval(
    timeout_hours=24,
    description="新しいイベントチャンネルとロールを作成します",
)
@app_commands.describe(
    channel_name="作成するイベントチャンネル名",
    members="ロールに追加するメンバー（スペース区切りでメンション）",
)
async def create_event_channel_cmd(
    ctx: discord.Interaction,
    channel_name: str,
    members: str | None = None,
):
    await create_event_channel_impl(ctx, channel_name, members)
```

### フロー例

1. **ユーザーAが `/event` コマンド実行**
   - ユーザーAは承認ロール未保持
2. **承認リクエスト送信**
   - メインチャンネル: 承認/拒否ボタン + Embed
   - スレッド作成: "承認: event"
   - スレッド内: リクエスト詳細Embed（コマンド名、引数など）
3. **承認者Bが承認ボタンクリック**
   - メインチャンネルのEmbedが承認結果Embedに更新
   - スレッド内に承認通知Embed投稿
   - コマンド実行（イベントチャンネル作成）
   - コマンドの結果（成功メッセージ）がスレッド内に投稿

## 注意事項

### デコレーター順序

**必ず以下の順序でデコレーターを適用してください**:

```python
@command_meta(...)      # 1. 最上位
@tree.command(...)      # 2. コマンド登録
@require_approval(...)  # 3. 承認ミドルウェア
@app_commands.describe(...)  # 4. 引数説明
async def command_cmd(...):
    pass
```

詳細は [docs/ADD_COMMAND.md](./ADD_COMMAND.md) を参照してください。

### エフェメラルメッセージの制限

スレッド内では `ephemeral=True` (一時的なメッセージ) がサポートされていません。`ThreadBoundResponse` と `ThreadBoundFollowup` では自動的に `ephemeral` パラメータを削除しています。

### 承認ロールの設定

承認ロール名は環境変数 `APPROVER_ROLE_NAME` で設定します。Discord サーバー内に該当するロールが存在しない場合、メンション部分にロール名がテキストとして表示されます。

## ベストプラクティス

### 1. 承認が必要なコマンド

以下のようなコマンドには承認フローを追加することを推奨します:

- **破壊的操作**: チャンネル削除、ロール削除など
- **リソース作成**: チャンネル作成、ロール作成など
- **権限変更**: ロール付与、権限設定など
- **重要な設定変更**: サーバー設定、Bot設定など

### 2. description パラメータの活用

`@require_approval` の `description` パラメータには、コマンドが何を実行するかを明確に記載してください:

```python
@require_approval(
    timeout_hours=48,
    description="全てのイベントチャンネルをアーカイブします（元に戻せません）"
)
```

### 3. タイムアウト時間の設定

コマンドの重要度に応じてタイムアウト時間を調整してください:

- **緊急度低**: 48時間以上
- **通常**: 24時間（デフォルト）
- **緊急度高**: 6〜12時間

### 4. ログの活用

承認システムは詳細なログを出力します。`logger.info` でフロー全体を追跡できるため、トラブルシューティング時に活用してください。

## トラブルシューティング

### 承認ロールメンションが表示されない

**原因**: 環境変数 `APPROVER_ROLE_NAME` に設定したロール名がDiscordサーバー内に存在しない

**解決方法**:
1. Discordサーバーの設定で該当するロールが存在するか確認
2. `.env` ファイルのロール名が正確か確認（大文字小文字も区別）

### コマンド実行結果がスレッド外に表示される

**原因**: コマンド内で `ctx.channel.send()` を使用している

**解決方法**: 必ず `ctx.response.send_message()` または `ctx.followup.send()` を使用してください。これらは `ThreadBoundInteraction` によってスレッドに自動リダイレクトされます。

### タイムアウト後もボタンが押せる

**原因**: クライアント側のViewキャッシュの問題（Discord側の仕様）

**動作**: ボタンをクリックしても既にViewが無効化されているため、実際には処理されません。

## 関連ドキュメント

- [ADD_COMMAND.md](./ADD_COMMAND.md) - コマンド追加手順（デコレーター順序）
- [UTILITIES.md](./UTILITIES.md) - ユーティリティ関数全般
- [ARCHITECTURE.md](./ARCHITECTURE.md) - アーキテクチャとパターン
- [DEVELOPMENT.md](./DEVELOPMENT.md) - 開発ワークフロー

## 参考: 承認システムのファイル一覧

```text
src/
├── utils/
│   ├── approval_config.py        # 設定管理（シングルトン）
│   ├── approval_decorator.py     # @require_approval デコレーター
│   └── approval_utils.py         # Embed作成、権限チェック
└── views/
    └── approval_view.py          # 承認/拒否ボタンUI、スレッド連携
```
