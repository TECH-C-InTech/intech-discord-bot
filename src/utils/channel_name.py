"""チャンネル名の正規化"""

import re


def normalize_channel_name(name: str) -> str:
    """Discordがテキストチャンネル名に行う正規化を近似する（小文字化、空白をハイフンに）

    Discordの正規化規則は公開されていないため、作成後の実際の名前でも検証し直すこと。
    """
    return re.sub(r"\s+", "-", name.strip()).lower()
