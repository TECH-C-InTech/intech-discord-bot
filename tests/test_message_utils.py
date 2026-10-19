from unittest.mock import AsyncMock, MagicMock

import discord

from src.utils.creation import Failed, Rejected
from src.utils.message_utils import report_creation_problem, send_private_reply


def http_error() -> discord.HTTPException:
    return discord.HTTPException(MagicMock(status=500, reason="error"), "error")


def make_ctx() -> MagicMock:
    ctx = MagicMock(spec=discord.Interaction)
    ctx.followup = MagicMock()
    ctx.followup.send = AsyncMock()
    ctx.edit_original_response = AsyncMock()
    ctx.response = MagicMock()
    ctx.response.is_done = MagicMock(return_value=True)
    return ctx


def sent_texts(ctx: MagicMock) -> str:
    return " ".join(str(call) for call in ctx.followup.send.await_args_list)


async def test_private_reply_replaces_thinking_message_when_followup_fails() -> None:
    ctx = make_ctx()
    ctx.followup.send = AsyncMock(side_effect=http_error())
    embed = discord.Embed(title="x")

    await send_private_reply(ctx, embed)

    ctx.edit_original_response.assert_awaited_once_with(embed=embed)


async def test_private_reply_does_not_raise_when_both_attempts_fail() -> None:
    ctx = make_ctx()
    ctx.followup.send = AsyncMock(side_effect=http_error())
    ctx.edit_original_response = AsyncMock(side_effect=http_error())

    await send_private_reply(ctx, discord.Embed(title="x"))


async def test_private_reply_does_not_touch_original_when_followup_succeeds() -> None:
    ctx = make_ctx()

    await send_private_reply(ctx, discord.Embed(title="x"))

    ctx.edit_original_response.assert_not_called()


async def test_rejection_reason_is_sent_as_is() -> None:
    ctx = make_ctx()

    await report_creation_problem(ctx, Rejected("上限に達しています"), "チャンネルの作成")

    assert "上限に達しています" in sent_texts(ctx)


async def test_leftover_channel_is_reported_for_manual_deletion() -> None:
    ctx = make_ctx()
    leftover = MagicMock(spec=discord.TextChannel)
    leftover.mention = "<#99>"

    await report_creation_problem(
        ctx, Failed(error=http_error(), leftover_channel=leftover), "チャンネルの作成"
    )

    assert "<#99>" in sent_texts(ctx)
    assert "削除" in sent_texts(ctx)
