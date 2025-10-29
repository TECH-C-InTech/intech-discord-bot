"""Discord Bot Commands"""

import importlib
from pathlib import Path

from discord import app_commands


def setup_all_commands(tree: app_commands.CommandTree):
    """
    全てのコマンドモジュールを自動検出して一括でセットアップする

    src/commands/ ディレクトリ内の .py ファイルを自動的に読み込みます。
    ただし、_ で始まるファイル（__init__.py, _sample.py など）は除外されます。

    Args:
        tree: Discord app_commands.CommandTree
    """
    # 現在のディレクトリを取得
    commands_dir = Path(__file__).parent

    # .pyファイルを検索（__init__.pyと_で始まるファイルは除外）
    for file_path in commands_dir.glob("*.py"):
        # ファイル名を取得
        module_name = file_path.stem

        # _ で始まるファイルはスキップ
        if module_name.startswith("_"):
            continue

        # モジュールを動的にインポート
        module = importlib.import_module(f".{module_name}", package=__package__)

        # setup 関数が存在する場合のみ実行
        if hasattr(module, "setup"):
            module.setup(tree)
        else:
            raise AttributeError(
                f"Module {module.__name__} does not have a setup function"
            )
