"""本人への返信やコマンドの説明に、利用者に分かりにくい語を使わない"""

from pathlib import Path
import re

# 「対象」「誘う」は、操作する人にとって何を指すのか分かりにくいので使わない
AVOIDED = re.compile(r"対象|誘")

SOURCES = [*Path("src").rglob("*.py"), Path("bot.py")]


def user_facing_strings(path: Path) -> list[str]:
    """コメントとdocstringを除いた、文字列リテラルの中身"""
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def test_user_facing_strings_avoid_unclear_words() -> None:
    found = [
        f"{path}: {text}"
        for path in SOURCES
        for text in user_facing_strings(path)
        if AVOIDED.search(text)
    ]

    assert found == []
