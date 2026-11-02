"""サーバーに登録されている絵文字とスタンプの一覧を、emoji_list.csvへ書き出す

Gatewayには接続せず、REST APIで読むだけ（Botはオンラインにならない）。メッセージは読まない。

    uv run scripts/export_emoji_list.py --guild-id <ID>

emoji_list.csvの列（BOM付きUTF-8）:

    ID: emojis.csvのemoji_id、stickers.csvのsticker_idとつなげる。削除済みのものや他のサーバーのものは載らない
    コード: 絵文字は :name: 、スタンプは名前
    種類: 絵文字 / アニメ絵文字 / スタンプ（形式）
    画像URL
"""

import argparse
import asyncio
from collections.abc import Sequence
from datetime import datetime
import os
from pathlib import Path

import discord
from dotenv import load_dotenv
from export_member_activity import DATA_ROOT, JST, write_csv

HEADER = ["ID", "コード", "種類", "画像URL"]

STICKER_FORMAT_LABELS = {
    discord.StickerFormatType.png: "PNG",
    discord.StickerFormatType.apng: "APNG",
    discord.StickerFormatType.lottie: "Lottie",
    discord.StickerFormatType.gif: "GIF",
}


def emoji_list_rows(emojis: Sequence[discord.Emoji], stickers: Sequence[discord.GuildSticker]) -> list[list]:
    """絵文字とスタンプの一覧の行を返す。スタンプには :name: のコードがないので名前を入れる"""
    return [
        *([e.id, f":{e.name}:", "アニメ絵文字" if e.animated else "絵文字", e.url] for e in emojis),
        *(
            [s.id, s.name, f"スタンプ（{STICKER_FORMAT_LABELS.get(s.format, '不明')}）", s.url]
            for s in stickers
        ),
    ]


async def export_emoji_list(guild: discord.Guild, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rows = emoji_list_rows(await guild.fetch_emojis(), await guild.fetch_stickers())
    write_csv(out / "emoji_list.csv", HEADER, rows)


async def run(token: str, guild_id: int, out: Path) -> None:
    async with discord.Client(intents=discord.Intents.none()) as client:
        await client.login(token)
        await export_emoji_list(await client.fetch_guild(guild_id), out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", default=".env", help="環境ファイルのパス（デフォルト: .env）")
    parser.add_argument("--guild-id", type=int, required=True, help="対象サーバーのID")
    parser.add_argument(
        "--out",
        type=Path,
        default=DATA_ROOT / f"{datetime.now(JST):%Y-%m}",
        help="書き出し先（デフォルト: member_activity_data/<実行した月>）",
    )
    args = parser.parse_args()

    load_dotenv(args.env)
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("❌ DISCORD_BOT_TOKEN が設定されていません")

    asyncio.run(run(token, args.guild_id, args.out))


if __name__ == "__main__":
    main()
