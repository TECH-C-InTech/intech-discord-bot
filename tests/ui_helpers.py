"""パネル（Components V2）の中身を取り出すテスト用の関数"""

import discord


def button_labels(view: discord.ui.LayoutView) -> list[str]:
    """ボタンの表示名を、画面に並ぶ順に返す"""
    return [
        item.item.label  # type: ignore[attr-defined]
        for item in view.walk_children()
        if isinstance(item, discord.ui.DynamicItem)
    ]


def texts(view: discord.ui.LayoutView) -> list[str]:
    """文字の部品の中身を、画面に並ぶ順に返す"""
    return [
        item.content for item in view.walk_children() if isinstance(item, discord.ui.TextDisplay)
    ]


def custom_ids(view: discord.ui.LayoutView) -> list[str]:
    return [
        item.custom_id  # type: ignore[attr-defined]
        for item in view.walk_children()
        if isinstance(item, discord.ui.DynamicItem)
    ]
