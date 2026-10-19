from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.records import (
    build_archive_notice_embed,
    build_archived_log_embed,
    build_creation_embed,
    build_members_added_embed,
    build_restored_embed,
    find_log_channel_problems,
    post_channel_record,
    post_log,
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

    assert embed.title == "新しいイベント"
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
    # ログチャンネルで読んでも対象が分かるよう、「このチャンネル」ではなくチャンネルを示す
    assert "<#10>" in join


def test_members_added_record_includes_actor_role_and_added_members() -> None:
    embed = build_members_added_embed(
        actor=mentionable("<@1>"),
        role=mentionable("<@&20>"),
        members=[mentionable("<@2>")],
    )

    assert embed.description == "<@1> が <@2> を <@&20> に加えました"


def test_archive_notice_says_who_archives_and_how_to_restore() -> None:
    embed = build_archive_notice_embed(
        actor=mentionable("<@1>"), restore_command="/restore_event_channel"
    )

    assert embed.description == "<@1> がアーカイブします"
    assert field(embed, "復元方法") == "`/restore_event_channel`"


def named_channel(mention: str, name: str) -> MagicMock:
    channel = mentionable(mention)
    channel.name = name
    return channel


def test_archived_log_says_who_archived_and_how_to_restore_that_channel() -> None:
    embed = build_archived_log_embed(
        actor=mentionable("<@1>"),
        channel=named_channel("<#10>", "e012-おでん会"),
        restore_command="/restore_event_channel",
    )

    assert embed.description == "<@1> が <#10> をアーカイブしました"
    assert field(embed, "復元方法") == "`/restore_event_channel channel_name:e012-おでん会`"


def test_restored_record_says_who_restored() -> None:
    embed = build_restored_embed(actor=mentionable("<@1>"), channel=mentionable("<#10>"))

    assert embed.description == "<@1> が <#10> を復元しました"


def make_guild_with_log_channel(name: str = "bot-log") -> tuple[MagicMock, MagicMock]:
    log_channel = MagicMock(spec=discord.TextChannel)
    log_channel.name = name
    log_channel.send = AsyncMock()
    guild = MagicMock(spec=discord.Guild)
    guild.text_channels = [log_channel]
    return guild, log_channel


async def test_log_is_sent_to_log_channel_without_notifying_anyone() -> None:
    guild, log_channel = make_guild_with_log_channel()
    embed = discord.Embed(title="x")

    await post_log(guild, "bot-log", embed)

    log_channel.send.assert_awaited_once()
    kwargs = log_channel.send.await_args.kwargs
    assert kwargs["embed"] is embed
    assert kwargs["allowed_mentions"].to_dict() == discord.AllowedMentions.none().to_dict()


async def test_log_is_skipped_when_log_channel_is_missing() -> None:
    guild, log_channel = make_guild_with_log_channel(name="other")

    await post_log(guild, "bot-log", discord.Embed(title="x"))

    log_channel.send.assert_not_called()


def http_error() -> discord.HTTPException:
    return discord.HTTPException(MagicMock(status=500, reason="error"), "error")


async def test_log_send_failure_does_not_raise() -> None:
    guild, log_channel = make_guild_with_log_channel()
    log_channel.send = AsyncMock(side_effect=http_error())

    await post_log(guild, "bot-log", discord.Embed(title="x"))


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


def test_missing_log_channel_is_reported() -> None:
    guild, _ = make_guild_with_log_channel(name="other")

    problems = find_log_channel_problems(guild, "bot-log")

    assert len(problems) == 1
    assert "bot-log" in problems[0]


def with_bot_permissions(log_channel: MagicMock, **permissions: bool) -> None:
    log_channel.permissions_for = MagicMock(return_value=discord.Permissions(**permissions))


def test_log_channel_without_send_permissions_is_reported() -> None:
    guild, log_channel = make_guild_with_log_channel()
    with_bot_permissions(log_channel, view_channel=True, send_messages=False, embed_links=True)

    problems = find_log_channel_problems(guild, "bot-log")

    assert len(problems) == 1
    assert "send_messages" in problems[0]


def test_log_channel_with_required_permissions_has_no_problems() -> None:
    guild, log_channel = make_guild_with_log_channel()
    with_bot_permissions(log_channel, view_channel=True, send_messages=True, embed_links=True)

    assert find_log_channel_problems(guild, "bot-log") == []


async def test_log_is_sent_when_configured_name_differs_only_in_case_and_spaces() -> None:
    guild, log_channel = make_guild_with_log_channel(name="bot-log")

    await post_log(guild, "Bot Log", discord.Embed(title="x"))

    log_channel.send.assert_awaited_once()


def test_log_channel_check_uses_normalized_name() -> None:
    guild, log_channel = make_guild_with_log_channel(name="bot-log")
    with_bot_permissions(log_channel, view_channel=True, send_messages=True, embed_links=True)

    assert find_log_channel_problems(guild, "Bot Log") == []


async def test_channel_record_labels_mentions_so_notifications_make_sense() -> None:
    channel = make_channel()
    invited = MagicMock(spec=discord.Member)
    invited.mention = "<@2>"

    await post_channel_record(
        channel, discord.Embed(title="x"), [invited], mention_label="参加者"
    )

    assert channel.send.await_args.kwargs["content"] == "参加者: <@2>"
