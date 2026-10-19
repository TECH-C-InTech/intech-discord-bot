from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.records import (
    build_archive_notice_embed,
    build_creation_embed,
    build_members_added_embed,
    build_restored_embed,
    delete_record,
    post_channel_record,
)


def mentionable(mention: str) -> MagicMock:
    obj = MagicMock()
    obj.mention = mention
    return obj


def text_of(embed: discord.Embed) -> str:
    return str(embed.to_dict())


def field(embed: discord.Embed, name: str) -> str | None:
    for f in embed.fields:
        if f.name == name:
            return f.value
    return None


def creation_embed(**overrides: object) -> discord.Embed:
    kwargs: dict[str, object] = {
        "kind": "イベント",
        "actor": mentionable("<@1>"),
        "channel": mentionable("<#10>"),
        "role": mentionable("<@&20>"),
        "members": [mentionable("<@1>"), mentionable("<@2>")],
        "failed_members": [],
        "join_command": "/add_event_role_member",
    }
    kwargs.update(overrides)
    return build_creation_embed(**kwargs)  # type: ignore[arg-type]


def test_creation_record_says_who_started_which_channel() -> None:
    embed = creation_embed()

    assert embed.title == "イベント作成"
    assert embed.description == "<@1> が <#10> を立てました"


def test_creation_record_lists_role_and_participants() -> None:
    embed = creation_embed()

    assert field(embed, "ロール") == "<@&20>"
    assert field(embed, "参加者") == "<@1>, <@2>"


def test_creation_record_lists_members_who_could_not_become_participants() -> None:
    embed = creation_embed(failed_members=[mentionable("<@9>")])

    assert field(embed, "参加者にできなかった人") == "<@9>"


def test_creation_record_tells_how_to_join() -> None:
    embed = creation_embed()

    join = field(embed, "参加方法")
    assert join is not None
    assert "/add_event_role_member" in join
    # 置き換える部分をコードの中に書かない（そのまま貼ると実行に失敗するため）
    assert "@自分" not in join
    # 参加方法は対象のチャンネルを示す
    assert "<#10>" in join


def test_members_added_record_includes_actor_role_and_added_members() -> None:
    embed = build_members_added_embed(
        actor=mentionable("<@1>"),
        role=mentionable("<@&20>"),
        members=[mentionable("<@2>")],
    )

    assert embed.title == "メンバー追加"
    assert embed.description == "<@1> が <@2> を <@&20> に加えました"


def test_archive_notice_says_who_archived_and_how_to_restore() -> None:
    embed = build_archive_notice_embed(
        actor=mentionable("<@1>"), restore_command="/restore_event_channel"
    )

    assert embed.title == "アーカイブ"
    assert embed.description == "<@1> がこのチャンネルをアーカイブしました"
    assert field(embed, "復元方法") == "`/restore_event_channel`"


def test_restored_record_says_who_restored() -> None:
    embed = build_restored_embed(actor=mentionable("<@1>"), channel=mentionable("<#10>"))

    assert embed.title == "復元"
    assert embed.description == "<@1> が <#10> を復元しました"


def http_error() -> discord.HTTPException:
    return discord.HTTPException(MagicMock(status=500, reason="error"), "error")


def make_channel() -> MagicMock:
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock(return_value=MagicMock(spec=discord.Message))
    return channel


async def test_channel_record_notifies_only_given_users() -> None:
    channel = make_channel()
    invited = MagicMock(spec=discord.Member)
    invited.mention = "<@2>"

    await post_channel_record(channel, discord.Embed(title="x"), [invited])

    kwargs = channel.send.await_args.kwargs
    assert kwargs["content"] == "<@2>"
    allowed = kwargs["allowed_mentions"].to_dict()
    assert allowed["users"] == [invited.id]
    assert allowed["parse"] == []


async def test_channel_record_without_users_has_no_content() -> None:
    channel = make_channel()

    await post_channel_record(channel, discord.Embed(title="x"))

    assert channel.send.await_args.kwargs["content"] is None


async def test_channel_record_send_failure_returns_none() -> None:
    channel = make_channel()
    channel.send = AsyncMock(side_effect=http_error())

    assert await post_channel_record(channel, discord.Embed(title="x")) is None


async def test_channel_record_labels_mentions_so_notifications_make_sense() -> None:
    channel = make_channel()
    invited = MagicMock(spec=discord.Member)
    invited.mention = "<@2>"

    await post_channel_record(channel, discord.Embed(title="x"), [invited], mention_label="参加者")

    assert channel.send.await_args.kwargs["content"] == "参加者: <@2>"


async def test_deleting_record_reports_success() -> None:
    message = MagicMock(spec=discord.Message)
    message.delete = AsyncMock()

    assert await delete_record(message) is True


async def test_deleting_record_reports_failure_without_raising() -> None:
    message = MagicMock(spec=discord.Message)
    message.delete = AsyncMock(side_effect=http_error())

    assert await delete_record(message) is False


def long_mentions(count: int) -> list[MagicMock]:
    # 18桁のIDのメンション（例: <@123456789012345678>）
    return [mentionable(f"<@{100000000000000000 + i}>") for i in range(count)]


def test_participant_fields_stay_within_discord_field_limit() -> None:
    members = long_mentions(45)

    embed = creation_embed(members=members)

    participant_fields = [f for f in embed.fields if f.name and f.name.startswith("参加者")]
    assert all(len(f.value or "") <= 1024 for f in participant_fields)
    joined = ", ".join(f.value or "" for f in participant_fields)
    assert all(m.mention in joined for m in members)
