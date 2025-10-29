# 新しいコマンドの追加方法

## 概要

このプロジェクトでは、コマンドモジュールを簡単に追加できる仕組みを採用しています。
**ファイルを作成するだけで自動的に登録されます！**

## 重要なルール

⚠️ **`@tree.command()` には必ず `name` パラメータを明示的に指定してください**

- デコレーターが続く場合、関数名を拾えないため、`name` で明示的に指定する必要があります
- コマンド名は一貫性を保つため、常に明示的に指定するルールとします

---

## 手順

### 1. 新しいコマンドモジュールを作成

`src/commands/` ディレクトリに新しいPythonファイルを作成します。

**例:** `src/commands/hello.py`

```python
"""挨拶コマンド"""

from logging import getLogger

import discord
from discord import app_commands

logger = getLogger(__name__)


async def hello_command(ctx: discord.Interaction, user: discord.User = None):
    """挨拶コマンドの実装"""
    target = user or ctx.user
    await ctx.response.send_message(f"こんにちは、{target.mention}さん！")


def setup(tree: app_commands.CommandTree):
    """挨拶コマンドを登録する"""
    
    # ✅ name パラメータを必ず指定する
    @tree.command(name="hello", description="挨拶をします")
    @app_commands.describe(user="挨拶する相手（省略時は自分）")
    async def hello_cmd(ctx: discord.Interaction, user: discord.User = None):
        await hello_command(ctx, user)
```

### 2. Botを起動

**それだけです！** `bot.py` を実行すれば、新しいコマンドが自動的に登録されます。

```bash
python bot.py
```

> **Note**: `src/commands/` 内の `.py` ファイルは自動的に検出されます。  
> ただし、`_` で始まるファイル（`__init__.py`, `_sample.py` など）は除外されます。

---

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

---

## テンプレート

`src/commands/_sample.py` にテンプレートがあります。
新しいコマンドを作成する際の参考にしてください。

---

## 利点

この仕組みには以下の利点があります：

✅ **超簡単な追加**: ファイルを作成するだけ（リスト編集不要！）  
✅ **疎結合**: 各コマンドモジュールは独立している  
✅ **保守性**: コマンドごとにファイルが分かれているため管理しやすい  
✅ **拡張性**: 新しいコマンドを追加しても既存のコードに影響しない  
✅ **テスタビリティ**: 各モジュールを個別にテスト可能

---

## 例: 複数のコマンドを持つモジュール

```python
"""ユーティリティコマンド集"""

from discord import app_commands
import discord

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
    
    # ✅ 各コマンドで name パラメータを明示的に指定
    @tree.command(name="ping", description="Botの応答速度を確認")
    async def ping_cmd(ctx: discord.Interaction):
        await ping_command(ctx)
    
    @tree.command(name="serverinfo", description="サーバー情報を表示")
    async def info_cmd(ctx: discord.Interaction):
        await info_command(ctx)
```
