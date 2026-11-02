"""メンバーチャンネル整理の定量分析用に、サーバーの活動データをCSVへ書き出す

本文はCSVに書き出さない。カスタム絵文字はIDと名前だけを抜き出す。
メンバーチャンネルのカテゴリ名は、引数か環境変数で指定する（引数が優先）:

    --member-categories member-channels member-channels-2
    --archive-member-category archived-member-channels

    MEMBER_CATEGORY_NAMES="member-channels,member-channels-2"  # カンマ区切り
    ARCHIVE_MEMBER_CATEGORY_NAME="archived-member-channels"

    uv run scripts/export_member_activity.py --guild-id <ID>
    uv run scripts/export_member_activity.py --guild-id <ID> --months 12

書き出したあとに、誰がリアクションしたかを別に取る（時間がかかる。止めても続きから再開できる）:

    uv run scripts/export_member_activity.py --guild-id <ID> --reactors

書き出し先は実行ごとに分かれる。前回と比べられるよう、既定では実行した月のフォルダに書く。
書き出し済みのフォルダには書かないので、同じ月に取り直すときは --out で別のフォルダを指定する:

    member_activity_data/
    ├── channel_owners.csv   実行をまたいで共有する。既存の行（手で直したものを含む）を残し、新しいチャンネルだけ追記する
    └── 2026-10/             実行ごとのCSV。--reactors を別の月に実行するときは --out で指定する

CSVの列（BOM付きUTF-8。日時は日本時間）:

    channels.csv: テキスト、フォーラム、ボイス、ステージの各チャンネル
        channel_id, name, category
        kind: member（メンバーチャンネル） / archived_member（退会者のチャンネル） / other
        position: カテゴリ内の並び順
        created_at

    members.csv: 書き出した時点のメンバー。退会者は含まない
        user_id, display_name, username, joined_at, is_bot

    channel_owners.csv: メンバーチャンネルの持ち主。チャンネル名と表示名の一致から推定する
        channel_id, channel_name, owner_user_id, owner_display_name
        match_status: unique（候補が1人） / ambiguous（複数。;区切り） / none（なし） / manual（手で直したもの）

    messages.csv: 期間内のメッセージ。スレッド内と、ボイスとステージのテキストチャットを含む
        message_id
        channel_id: スレッド内なら親チャンネルのID
        thread_id: スレッド内ならスレッドのID。それ以外は空
        author_id, author_is_bot
        message_type: default, reply のほか、システムメッセージも含む
        created_at
        reply_to_message_id, reply_to_author_id: 返信のときだけ入る。返信先が消えていると投稿者は空
        reaction_count: 付いたリアクションの合計数

    stickers.csv: 使われたスタンプ。1回の使用につき1行
        message_id, sticker_id, sticker_name

    emojis.csv: 本文中のカスタム絵文字。1回の使用につき1行。標準の絵文字は含まない
        message_id, emoji_id, emoji_name

    reactions.csv: 誰がリアクションしたか（--reactors で作る）
        message_id, emoji, user_id
        reaction_type: normal（通常） / burst（スーパーリアクション）
"""

import argparse
import asyncio
from collections import Counter
from collections.abc import AsyncIterator
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from logging import basicConfig, getLogger
import os
from pathlib import Path
import re
from typing import Any

import discord
from dotenv import load_dotenv

logger = getLogger(__name__)
basicConfig(level="INFO")

JST = timezone(timedelta(hours=9))

DATA_ROOT = Path("member_activity_data")

CHANNELS_HEADER = ["channel_id", "name", "category", "kind", "position", "created_at"]
MEMBERS_HEADER = ["user_id", "display_name", "username", "joined_at", "is_bot"]
OWNERS_HEADER = ["channel_id", "channel_name", "owner_user_id", "owner_display_name", "match_status"]
MESSAGES_HEADER = [
    "message_id",
    "channel_id",
    "thread_id",
    "author_id",
    "author_is_bot",
    "message_type",
    "created_at",
    "reply_to_message_id",
    "reply_to_author_id",
    "reaction_count",
]
STICKERS_HEADER = ["message_id", "sticker_id", "sticker_name"]
EMOJIS_HEADER = ["message_id", "emoji_id", "emoji_name"]
REACTIONS_HEADER = ["message_id", "emoji", "user_id", "reaction_type"]

CUSTOM_EMOJI = re.compile(r"<a?:([A-Za-z0-9_~\-]+):(\d+)>")


@dataclass(frozen=True)
class MemberCategories:
    """メンバーチャンネルのカテゴリ名"""

    member: frozenset[str]
    archived: str


def resolve_member_categories(member_args: list[str] | None, archived_arg: str | None) -> MemberCategories:
    """引数、環境変数の順にカテゴリ名を決める。どちらもないと全チャンネルがotherになるので止める"""
    member_names = member_args or os.getenv("MEMBER_CATEGORY_NAMES", "").split(",")
    archived = (archived_arg or os.getenv("ARCHIVE_MEMBER_CATEGORY_NAME", "")).strip()
    member = frozenset(n.strip() for n in member_names if n.strip())
    if not member or not archived:
        raise SystemExit(
            "❌ メンバーチャンネルのカテゴリ名がありません。"
            "--member-categories と --archive-member-category、"
            "または MEMBER_CATEGORY_NAMES と ARCHIVE_MEMBER_CATEGORY_NAME を指定してください"
        )
    return MemberCategories(member=member, archived=archived)


def channel_kind(category_name: str | None, categories: MemberCategories) -> str:
    """カテゴリ名からチャンネルの種類（member / archived_member / other）を返す"""
    if category_name in categories.member:
        return "member"
    if category_name == categories.archived:
        return "archived_member"
    return "other"


def category_name(channel: discord.abc.GuildChannel) -> str | None:
    return channel.category.name if channel.category else None


def normalize(name: str) -> str:
    """小文字化し、空白（全角含む）とハイフンを取り除く。「山田 太郎」と「山田太郎」「山田-太郎」を同じに扱う"""
    return re.sub(r"[\s\-]+", "", name.lower())


def owner_candidates(channel_name: str, members: list[discord.Member]) -> list[discord.Member]:
    """チャンネル名が表示名・ユーザー名のどれかに含まれるメンバーを返す"""
    target = normalize(channel_name)
    found = []
    for m in members:
        if m.bot:
            continue
        names = {m.display_name, m.global_name or "", m.name}
        if any(target and target in normalize(n) for n in names if n):
            found.append(m)
    return found


def jst(dt: datetime | None) -> str:
    return dt.astimezone(JST).isoformat(timespec="seconds") if dt else ""


def channel_row(channel: discord.abc.GuildChannel, categories: MemberCategories) -> list:
    name = category_name(channel)
    kind = channel_kind(name, categories)
    return [channel.id, channel.name, name or "", kind, channel.position, jst(channel.created_at)]


def member_row(member: discord.Member) -> list:
    return [member.id, member.display_name, member.name, jst(member.joined_at), member.bot]


def owner_row(channel: discord.abc.GuildChannel, members: list[discord.Member]) -> list:
    found = owner_candidates(channel.name, members)
    status = "unique" if len(found) == 1 else "ambiguous" if found else "none"
    return [
        channel.id,
        channel.name,
        ";".join(str(m.id) for m in found),
        ";".join(m.display_name for m in found),
        status,
    ]


def merge_owner_rows(existing: list[list[str]], found: list[list]) -> list[list]:
    """既存の行をすべて残し、まだ行のないチャンネルだけを足す

    退会したメンバーは推定し直すと見つからないので、分かっている持ち主は上書きしない。
    """
    known = {row[0] for row in existing}
    return [*existing, *(row for row in found if str(row[0]) not in known)]


def message_row(msg: discord.Message, source: discord.abc.GuildChannel | discord.Thread) -> list:
    # 転送やピン留めの通知にもreferenceが付くので、返信のときだけ返信先を入れる
    ref = msg.reference if msg.type is discord.MessageType.reply else None
    resolved = ref.resolved if ref else None
    is_thread = isinstance(source, discord.Thread)
    return [
        msg.id,
        source.parent_id if is_thread else source.id,
        source.id if is_thread else "",
        msg.author.id,
        msg.author.bot,
        msg.type.name,
        jst(msg.created_at),
        ref.message_id if ref and ref.message_id else "",
        resolved.author.id if isinstance(resolved, discord.Message) else "",
        sum(r.count for r in msg.reactions),
    ]


def sticker_rows(msg: discord.Message) -> list[list]:
    """メッセージに付いたスタンプを1つ1行で返す"""
    return [[msg.id, s.id, s.name] for s in msg.stickers]


def emoji_rows(msg: discord.Message) -> list[list]:
    """本文中のカスタム絵文字を、1回の使用につき1行で返す。本文そのものは残さない"""
    return [[msg.id, emoji_id, name] for name, emoji_id in CUSTOM_EMOJI.findall(msg.content)]


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    # Excelで開いても文字化けしないようBOM付きにする
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    logger.info(f"📝 {path} ({len(rows)} rows)")


def read_messages(out: Path) -> list[dict[str, str]]:
    """書き出し済みのmessages.csvを読む"""
    path = out / "messages.csv"
    if not path.exists():
        raise SystemExit(
            f"❌ {path} がありません。"
            "書き出し済みのフォルダを --out で指定するか、先に --reactors なしで書き出してください"
        )
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_owner_rows(path: Path) -> list[list[str]]:
    """書き出し済みのchannel_owners.csvの行を読む。なければ空を返す"""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))[1:]


async def collect_threads(guild: discord.Guild) -> list[discord.Thread]:
    """アクティブなスレッドと、アーカイブ済みのスレッドをすべて集める"""
    threads: dict[int, discord.Thread] = {t.id: t for t in await guild.active_threads()}
    parents: list[discord.TextChannel | discord.ForumChannel] = [
        *guild.text_channels,
        *guild.forums,
    ]
    for parent in parents:
        # フォーラムには非公開スレッドがない。非公開スレッドを読む権限がなければ公開分だけにする
        listings = [parent.archived_threads(limit=None)]
        if isinstance(parent, discord.TextChannel):
            listings.append(parent.archived_threads(limit=None, private=True))
        for i, listing in enumerate(listings):
            try:
                async for t in listing:
                    threads[t.id] = t
            except (discord.Forbidden, discord.NotFound):
                if i == 0:
                    logger.warning(f"⚠️ スレッド一覧を読めません: #{parent.name}")
    return list(threads.values())


async def iter_messages(
    guild: discord.Guild, **history_options: Any
) -> AsyncIterator[tuple[discord.Message, Any]]:
    """テキスト、ボイス、ステージの各チャンネルとスレッドの履歴を順に読む。読めないものや、途中で消えたものは飛ばす"""
    sources = [
        *guild.text_channels,
        *guild.voice_channels,
        *guild.stage_channels,
        *await collect_threads(guild),
    ]
    for i, source in enumerate(sources, 1):
        count = 0
        try:
            async for msg in source.history(limit=None, oldest_first=True, **history_options):
                count += 1
                yield msg, source
        except (discord.Forbidden, discord.NotFound):
            logger.warning(f"⚠️ 履歴を読めません: #{source.name}")
            continue
        logger.info(f"[{i}/{len(sources)}] #{source.name}: {count} messages")


async def export(
    guild: discord.Guild, months: int, out: Path, owners_path: Path, categories: MemberCategories
) -> None:
    """活動データのCSVを書き出す"""
    # 上書きすると、前回の結果や別の実行のreactions.csvと混ざる
    if (out / "messages.csv").exists():
        raise SystemExit(f"❌ {out} は書き出し済みです。--out で別のフォルダを指定してください")

    channels = [
        c
        for c in guild.channels
        if isinstance(c, discord.TextChannel | discord.ForumChannel | discord.VoiceChannel | discord.StageChannel)
    ]
    # 名前の間違いに、時間のかかる履歴の取得を終えてから気づくことのないよう、先に止める
    if not any(channel_kind(category_name(c), categories) == "member" for c in channels):
        raise SystemExit(f"❌ メンバーチャンネルが見つかりません。カテゴリ名を確認してください: {sorted(categories.member)}")

    out.mkdir(parents=True, exist_ok=True)
    owners_path.parent.mkdir(parents=True, exist_ok=True)

    in_order = sorted(channels, key=lambda c: (c.category.position if c.category else -1, c.position))
    write_csv(out / "channels.csv", CHANNELS_HEADER, [channel_row(c, categories) for c in in_order])

    members = list(guild.members)
    write_csv(out / "members.csv", MEMBERS_HEADER, [member_row(m) for m in members])

    member_channels = [c for c in channels if channel_kind(category_name(c), categories) != "other"]
    existing_owners = read_owner_rows(owners_path)
    owners = merge_owner_rows(existing_owners, [owner_row(c, members) for c in member_channels])
    write_csv(owners_path, OWNERS_HEADER, owners)
    logger.info(f"👤 channel_owners.csvに {len(owners) - len(existing_owners)} 件追加しました")

    since = datetime.now(timezone.utc) - timedelta(days=round(months * 30.44))
    messages, stickers, emojis = [], [], []
    async for msg, source in iter_messages(guild, after=since):
        messages.append(message_row(msg, source))
        stickers.extend(sticker_rows(msg))
        emojis.extend(emoji_rows(msg))
    write_csv(out / "messages.csv", MESSAGES_HEADER, messages)
    write_csv(out / "stickers.csv", STICKERS_HEADER, stickers)
    write_csv(out / "emojis.csv", EMOJIS_HEADER, emojis)
    logger.info(f"✅ 書き出しました: {out}")


def load_reactors_progress(reactions_path: Path, done_path: Path, expected: dict[str, int]) -> set[str]:
    """前回の進捗を読み、取り直しが要らないメッセージのIDを返す

    重複した行を消す。記録済みでも行が足りないメッセージは取り直す。記録の途中で止まった行は消しておく。
    """
    done = set(done_path.read_text().split()) if done_path.exists() else set()
    existing: dict[tuple[str, ...], None] = {}
    if reactions_path.exists():
        with reactions_path.open(encoding="utf-8-sig", newline="") as f:
            # reaction_typeがなかったころの行は、通常のリアクションだけが入っている
            existing = dict.fromkeys(
                (r["message_id"], r["emoji"], r["user_id"], r.get("reaction_type") or "normal")
                for r in csv.DictReader(f)
            )
    counts = Counter(r[0] for r in existing)
    done = {m for m in done if counts[m] >= expected.get(m, 0)}
    write_csv(reactions_path, REACTIONS_HEADER, [list(r) for r in existing if r[0] in done])
    done_path.write_text("".join(f"{m}\n" for m in sorted(done)))
    return done


async def export_reactors(client: discord.Client, out: Path) -> None:
    """messages.csvでリアクションが付いているメッセージについて、誰が押したかをreactions.csvへ追記する

    1メッセージ取り終えるごとに reactions_done.txt へ記録するので、止めても続きから再開できる。
    """
    targets = [row for row in read_messages(out) if int(row["reaction_count"]) > 0]
    reactions_path = out / "reactions.csv"
    done_path = out / "reactions_done.txt"
    expected = {row["message_id"]: int(row["reaction_count"]) for row in targets}
    done = load_reactors_progress(reactions_path, done_path, expected)

    remaining = [row for row in targets if row["message_id"] not in done]
    logger.info(f"🔁 リアクション付き {len(targets)} 件のうち、残り {len(remaining)} 件を取ります")

    channels: dict[int, Any] = {}
    with reactions_path.open("a", encoding="utf-8", newline="") as rf, done_path.open("a") as df:
        writer = csv.writer(rf)
        for i, row in enumerate(remaining, 1):
            channel_id = int(row["thread_id"] or row["channel_id"])
            try:
                if channel_id not in channels:
                    channels[channel_id] = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
                msg = await channels[channel_id].fetch_message(int(row["message_id"]))
                rows = []
                for r in msg.reactions:
                    # typeを省くと通常のリアクションしか返らない
                    types = [discord.ReactionType.normal]
                    if r.burst_count:
                        types.append(discord.ReactionType.burst)
                    for reaction_type in types:
                        async for u in r.users(type=reaction_type):
                            rows.append([msg.id, str(r.emoji), u.id, reaction_type.name])
                writer.writerows(rows)
            except (discord.NotFound, discord.Forbidden) as e:
                # 消されたメッセージや読めないチャンネルは飛ばす
                logger.warning(f"⚠️ 取れませんでした: message {row['message_id']} ({type(e).__name__})")
            rf.flush()
            df.write(row["message_id"] + "\n")
            df.flush()
            if i % 100 == 0 or i == len(remaining):
                logger.info(f"[{i}/{len(remaining)}]")
    logger.info(f"✅ 書き出しました: {reactions_path}")


async def run_mode(client: discord.Client, args: argparse.Namespace) -> None:
    """指定されたモードの書き出しを実行する"""
    if args.reactors:
        await export_reactors(client, args.out)
        return
    guild = client.get_guild(args.guild_id)
    if guild is None:
        raise SystemExit(f"❌ サーバーが見つかりません: {args.guild_id}")
    categories = resolve_member_categories(args.member_categories, args.archive_member_category)
    await export(guild, args.months, args.out, args.owners, categories)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", default=".env", help="環境ファイルのパス（デフォルト: .env）")
    parser.add_argument("--guild-id", type=int, required=True, help="対象サーバーのID")
    parser.add_argument("--months", type=int, default=12, help="さかのぼる月数（デフォルト: 12）")
    parser.add_argument(
        "--out",
        type=Path,
        default=DATA_ROOT / f"{datetime.now(JST):%Y-%m}",
        help="書き出し先（デフォルト: member_activity_data/<実行した月>）",
    )
    parser.add_argument(
        "--owners",
        type=Path,
        default=DATA_ROOT / "channel_owners.csv",
        help="持ち主の対応表（デフォルト: member_activity_data/channel_owners.csv）",
    )
    parser.add_argument(
        "--member-categories",
        nargs="+",
        help="メンバーチャンネルのカテゴリ名。複数指定できる（デフォルト: 環境変数 MEMBER_CATEGORY_NAMES）",
    )
    parser.add_argument(
        "--archive-member-category",
        help="退会者のチャンネルのカテゴリ名（デフォルト: 環境変数 ARCHIVE_MEMBER_CATEGORY_NAME）",
    )
    parser.add_argument(
        "--reactors",
        action="store_true",
        help="書き出し済みのmessages.csvから、誰がリアクションしたかだけを取る（再開できる）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    load_dotenv(args.env)
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("❌ DISCORD_BOT_TOKEN が設定されていません")
    # 接続する前に、設定の不足で止める
    if not args.reactors:
        resolve_member_categories(args.member_categories, args.archive_member_category)

    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)

    started = False
    failed = False

    @client.event
    async def on_ready() -> None:
        # 再接続のたびに on_ready が呼ばれるので、書き出しは一度だけ始める
        nonlocal started, failed
        if started:
            return
        started = True
        try:
            await run_mode(client, args)
        except Exception:
            # イベント内の例外はdiscord.pyがログに出すだけで、終了コードに表れない
            logger.exception("❌ 書き出しに失敗しました")
            failed = True
        finally:
            await client.close()

    asyncio.run(client.start(token))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
