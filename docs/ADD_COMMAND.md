# 新しいコマンドの追加方法

## 概要

このプロジェクトでは、コマンドモジュールを簡単に追加できる仕組みを採用しています。
**ファイルを作成するだけで自動的に登録されます！**

## 重要なルール

⚠️ **`@tree.command()` には必ず `name` パラメータを明示的に指定してください**

- デコレーターが続く場合、関数名を拾えないため、`name` で明示的に指定する必要があります
- コマンド名は一貫性を保つため、常に明示的に指定するルールとします

⚠️ **コマンドには必ず `@command_meta()` デコレーターを付けてください**

- `/help` と `/docs` コマンドで自動的に表示されるメタデータを登録します
- カテゴリー、アイコン、短い説明、使用例などを定義できます
- **デコレーターの順序: `@command_meta()` → `@tree.command()` → `@app_commands.describe()` → 関数定義**

## 手順

### 1. 新しいコマンドモジュールを作成

`src/commands/` ディレクトリに新しいPythonファイルを作成します。

**例:** `src/commands/hello.py`

```python
"""挨拶コマンド"""

from logging import getLogger

import discord
from discord import app_commands

from ..utils.command_metadata import command_meta

logger = getLogger(__name__)


async def hello_command(ctx: discord.Interaction, user: discord.User = None):
    """挨拶コマンドの実装"""
    target = user or ctx.user
    await ctx.response.send_message(f"こんにちは、{target.mention}さん！")


def setup(tree: app_commands.CommandTree):
    """挨拶コマンドを登録する"""
    
    # ✅ デコレーターの順序を守る: @command_meta → @tree.command → @app_commands.describe
    @command_meta(
        category="ユーティリティ",
        icon="👋",
        short_description="指定したユーザーに挨拶する",
        examples=[
            "`/hello` - 自分に挨拶",
            "`/hello user:@someone` - 他のユーザーに挨拶",
        ],
    )
    @tree.command(name="hello", description="挨拶をします")
    @app_commands.describe(user="挨拶する相手（省略時は自分）")
    async def hello_cmd(ctx: discord.Interaction, user: discord.User = None):
        await hello_command(ctx, user)
```

### 2. Botを起動

**それだけです！** `bot.py` を実行すれば、新しいコマンドが自動的に登録されます。

```bash
uv run bot.py
```

> **Note**: `src/commands/` 内の `.py` ファイルは自動的に検出されます。  
> ただし、`_` で始まるファイル（`__init__.py`, `_sample.py` など）は除外されます。

## コマンドモジュールの構成要素

### 必須要素

1. **`setup(tree)` 関数**
   - コマンドを `tree` に登録する関数
   - この関数が自動的に呼び出されます

2. **`name` パラメータの明示的な指定**
   - `@tree.command(name="コマンド名", description="説明")` の形式で記述
   - 関数名からの自動推論は使用しない

### 推奨要素

1. **モジュールレベルのdocstring**
   - ファイルの先頭にコマンドの説明を記載

2. **ロガーの設定**

   ```python
   from logging import getLogger
   logger = getLogger(__name__)
   ```

3. **実装関数と登録の分離**
   - コマンドのロジックは別関数として実装
   - `setup()` 内でデコレータを使って登録

4. **コマンドメタデータの登録**
   - `@command_meta()` デコレーターで `/help` と `/docs` 用のメタデータを定義
   - **必ず最上位のデコレーターとして配置する**
   - 後述の「コマンドメタデータの使い方」を参照

## コマンドメタデータの使い方

`@command_meta()` デコレーターを使うことで、コマンドのメタデータを自動的に `/help` と `/docs` コマンドに反映できます。

### メタデータの項目

| パラメータ | 必須 | 説明 | 例 |
|-----------|------|------|-----|
| `category` | ✅ | コマンドのカテゴリー | `"イベントチャンネル管理"` |
| `icon` | ✅ | カテゴリーアイコン（絵文字） | `"📅"` |
| `short_description` | 推奨 | `/help` で表示される短い説明 | `"イベント用のチャンネルを作成"` |
| `restrictions` | 任意 | 実行制限の説明 | `"• イベントリクエストチャンネルでのみ実行可能"` |
| `examples` | 推奨 | 使用例のリスト | `["/hello user:@someone"]` |
| `notes` | 任意 | 追加の注意事項 | `"メンバーが50人を超える場合は分割表示"` |

### 使用例

```python
from ..utils.command_metadata import command_meta

@command_meta(
    category="イベント管理",
    icon="📅",
    short_description="新しいイベントを作成",
    restrictions="• イベントリクエストチャンネルでのみ実行可能",
    examples=[
        "`/create_event name:ハッカソン`",
        "`/create_event name:勉強会 members:@user1 @user2`",
    ],
    notes="イベント名は50文字以内で指定してください",
)
@tree.command(name="create_event", description="イベントを作成します")
@app_commands.describe(
    name="イベント名",
    members="参加メンバー（任意）",
)
async def create_event_cmd(ctx: discord.Interaction, name: str, members: str = None):
    await create_event(ctx, name, members)
```

### デコレーターの順序（重要）

必ず以下の順序でデコレーターを適用してください：

1. `@command_meta()` - **最上位**: メタデータの登録
2. `@tree.command()` - コマンドの登録
3. `@require_channel()` - チャンネル制限（必要な場合）
4. `@require_approval()` - 承認ミドルウェア（必要な場合）
5. `@app_commands.describe()` - パラメータの説明
6. `@app_commands.choices()` - 選択肢（必要な場合）
7. 関数定義

**チャンネル制限と承認の両方を使う場合の注意**:
- `@require_channel` は `@require_approval` より上位に配置してください
- これにより、承認リクエスト送信前にチャンネル制限をチェックでき、不正なチャンネルでの無駄な承認フローを防げます

#### ❌ 間違った順序

```python
@tree.command(...)  # これが先だとメタデータが登録されない
@command_meta(...)
async def my_command(...):
    ...
```

#### ✅ 正しい順序（基本）

```python
@command_meta(...)  # メタデータを最初に
@tree.command(...)
@app_commands.describe(...)
async def my_command(...):
    ...
```

#### ✅ 正しい順序（チャンネル制限 + 承認）

```python
@command_meta(...)          # 1. メタデータ
@tree.command(...)          # 2. コマンド登録
@require_channel(...)       # 3. チャンネル制限（先にチェック）
@require_approval(...)      # 4. 承認ミドルウェア
@app_commands.describe(...) # 5. パラメータ説明
async def my_command(...):
    ...
```

#### ✅ 承認ミドルウェアのみを使用する場合

```python
from ..utils.approval_decorator import require_approval

@command_meta(...)               # メタデータを最初に
@tree.command(...)               # Discord登録
@require_approval(               # 承認ミドルウェア（tree.commandの直後）
    timeout_hours=24,
    description="新しいチャンネルを作成します"
)
@app_commands.describe(...)      # パラメータの説明
async def my_command(...):
    ...
```

**承認ミドルウェアについて:**
- `@require_approval()` デコレーターを使用すると、Administrator以外のユーザーは承認が必要になります
- Administratorユーザーは承認不要で即座にコマンドが実行されます
- 詳細は [UTILITIES.md](./UTILITIES.md#承認ミドルウェア) を参照してください

## テンプレート

`src/commands/_sample.py` にテンプレートがあります。
新しいコマンドを作成する際の参考にしてください。

## 利点

この仕組みには以下の利点があります：

✅ **超簡単な追加**: ファイルを作成するだけ（リスト編集不要！）  
✅ **疎結合**: 各コマンドモジュールは独立している  
✅ **保守性**: コマンドごとにファイルが分かれているため管理しやすい  
✅ **拡張性**: 新しいコマンドを追加しても既存のコードに影響しない  
✅ **テスタビリティ**: 各モジュールを個別にテスト可能

## 例: 複数のコマンドを持つモジュール

```python
"""ユーティリティコマンド集"""

from discord import app_commands
import discord

from ..utils.command_metadata import command_meta

async def ping_command(ctx: discord.Interaction):
    """Ping コマンド"""
    latency = round(ctx.client.latency * 1000)
    await ctx.response.send_message(f"🏓 Pong! {latency}ms")

async def info_command(ctx: discord.Interaction):
    """サーバー情報コマンド"""
    guild = ctx.guild
    embed = discord.Embed(title=guild.name, color=discord.Color.blue())
    embed.add_field(name="メンバー数", value=guild.member_count)
    await ctx.response.send_message(embed=embed)

def setup(tree: app_commands.CommandTree):
    """複数のコマンドを登録"""
    
    @command_meta(
        category="ユーティリティ",
        icon="🔧",
        short_description="Botの応答速度を確認",
        examples=["`/ping`"],
    )
    @tree.command(name="ping", description="Botの応答速度を確認")
    async def ping_cmd(ctx: discord.Interaction):
        await ping_command(ctx)
    
    @command_meta(
        category="ユーティリティ",
        icon="🔧",
        short_description="サーバーの基本情報を表示",
        examples=["`/serverinfo`"],
    )
    @tree.command(name="serverinfo", description="サーバー情報を表示")
    async def info_cmd(ctx: discord.Interaction):
        await info_command(ctx)
```
