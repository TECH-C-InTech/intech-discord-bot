"""クラブチャンネル管理コマンド"""

from logging import getLogger

import discord
from discord import app_commands

from ..utils.channel_config import ChannelConfig
from ..utils.channel_utils import (
    resolve_target_text_channel_or_error,
    thread_target_note,
    validate_category_exists,
)
from ..utils.club_name import validate_club_name
from ..utils.command_metadata import command_meta
from ..utils.creation import Created, Rejected, create_channel_with_role
from ..utils.message_utils import (
    create_success_embed,
    handle_command_error,
    report_creation_problem,
    send_error_message,
    send_private_reply,
)
from ..utils.records import (
    build_creation_embed,
    build_members_added_embed,
    post_channel_record,
    post_log,
)
from ..utils.role_utils import describe_grant, grant_role, with_creator
from ..utils.validation_utils import (
    parse_member_mentions,
    parse_role_mention,
    validate_role_safety,
)

logger = getLogger(__name__)


# ==================== コマンド実装関数 ====================


async def create_club_channel_impl(
    ctx: discord.Interaction,
    channel_name: str,
    members: str | None = None,
):
    """クラブチャンネルを作成する

    Args:
        ctx: Discord Interaction
        channel_name: 作成するクラブチャンネル名
        members: ロールに追加するメンバー（メンション形式）
    """
    # 環境変数を一括取得
    config = await ChannelConfig.load(ctx)
    if not config:
        return

    # カテゴリーの存在確認
    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return

    category_channel = await validate_category_exists(ctx, guild, config.club_category_name)
    if not category_channel:
        return

    # メンバーが指定されている場合、メンションから抽出
    member_objects: list[discord.Member] = []
    if members:
        parsed_members = await parse_member_mentions(ctx, members, guild)
        if parsed_members is None:
            return
        member_objects = parsed_members

    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    # クラブはチャンネルとロールを名前で結びつけるため、既存のロールや番号と衝突する名前を拒否する
    def validate(
        guild: discord.Guild, name: str, *, exclude: discord.TextChannel | None = None
    ) -> str | None:
        return validate_club_name(
            name,
            log_channel_name=config.log_channel_name,
            existing_role_names=[role.name for role in guild.roles],
            existing_channel_names=[
                ch.name
                for ch in category_channel.text_channels
                if exclude is None or ch.id != exclude.id
            ],
        )

    def decide_name(guild: discord.Guild, category: discord.CategoryChannel) -> str | Rejected:
        reason = validate(guild, channel_name)
        return Rejected(reason) if reason is not None else channel_name

    try:
        outcome = await create_channel_with_role(
            guild,
            category_channel,
            decide_name=decide_name,
            # Discordが正規化した実際の名前で検証し直す（作成したチャンネル自身は除く）
            validate_created_name=lambda guild, channel: validate(
                guild, channel.name, exclude=channel
            ),
            # ロールはチャンネルの実際の名前で作り、名前の紐づけがずれないようにする
            role_name_for=lambda channel: channel.name,
        )
    except Exception as e:
        await handle_command_error(ctx, e, "クラブチャンネルの作成")
        return

    if not isinstance(outcome, Created):
        await report_creation_problem(ctx, outcome, "クラブチャンネルの作成")
        return

    channel, role = outcome.channel, outcome.role
    # 立てた人は、その時点で参加者になる
    participants = (
        with_creator(member_objects, ctx.user)
        if isinstance(ctx.user, discord.Member)
        else member_objects
    )
    grant = await grant_role(participants, role)

    description = f"{channel.mention} と {role.mention} を作成しました"
    grant_description = describe_grant(grant)
    if grant_description:
        description += f"\n{grant_description}"
    await send_private_reply(
        ctx,
        create_success_embed(
            title="クラブチャンネル作成完了",
            description=description,
            チャンネル名=channel.name,
            ロール付与人数=len(grant.granted),
        ),
    )
    logger.info(
        f"Created club channel: {channel.name} and role "
        f"with {len(grant.granted)} members by {ctx.user}"
    )

    def record() -> discord.Embed:
        return build_creation_embed(
            kind="クラブ",
            actor=ctx.user,
            channel=channel,
            role=role,
            members=grant.granted,
            failed_members=grant.failed,
            join_command="/add_club_role_member",
        )

    # 立てた本人には通知しない
    invited = [member for member in grant.granted if member.id != ctx.user.id]
    await post_channel_record(channel, record(), mention_users=invited)
    await post_log(guild, config.log_channel_name, record())


async def add_club_role_member_impl(
    ctx: discord.Interaction,
    members: str,
    role_name: str | None = None,
):
    """クラブロールにメンバーを追加する

    実行可能なロールはCLUB_CATEGORY_NAMEカテゴリのチャンネルに対応するものだけ

    Args:
        ctx: Discord Interaction
        members: 追加するメンバー（メンション形式）
        role_name: 対象のロール名（省略時は実行チャンネル名）
    """
    # 環境変数を一括取得
    config = await ChannelConfig.load(ctx)
    if not config:
        return

    guild = ctx.guild
    if guild is None:
        await send_error_message(ctx, "このコマンドはサーバー内でのみ実行できます。")
        return

    # カテゴリーの存在確認
    club_category = await validate_category_exists(ctx, guild, config.club_category_name)
    if not club_category:
        return

    via_thread = False
    # role_nameが省略された場合は実行チャンネル（スレッドなら親チャンネル）の名前を使用
    if role_name is None:
        target_channel, via_thread = await resolve_target_text_channel_or_error(ctx)
        if target_channel is None:
            return
        # 対象チャンネルがCLUB_CATEGORY_NAMEカテゴリーに属しているか確認
        if target_channel.category_id != club_category.id:
            await send_error_message(
                ctx,
                f"このコマンドは {config.club_category_name} カテゴリー内でのみ実行できます。",
            )
            return
        role_name = target_channel.name
        # ロールを名前で検索
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            await send_error_message(ctx, f"ロール `{role_name}` が見つかりません。")
            return
    else:
        # role_nameが指定された場合、パース関数でロールを取得
        role = await parse_role_mention(ctx, role_name, guild)
        if not role:
            return
        role_name = role.name

    # ロールの安全性チェック
    if not await validate_role_safety(ctx, role):
        return

    # 同名のチャンネルがCLUB_CATEGORY_NAMEカテゴリーに存在するか確認
    channel_dict = {ch.name: ch for ch in club_category.text_channels}
    club_channel = channel_dict.get(role_name)
    if not club_channel:
        await send_error_message(
            ctx,
            f"ロール {role.mention} に対応するクラブチャンネルが見つかりません。\n"
            f"このコマンドは{config.club_category_name}カテゴリー内のチャンネルに対応するロールのみ操作可能です。",
        )
        return

    # メンバーをメンションから抽出
    member_objects = await parse_member_mentions(ctx, members, guild)
    if member_objects is None:
        return

    # 応答を保留
    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=True, thinking=True)

    grant = await grant_role(member_objects, role)

    note = thread_target_note(club_channel, via_thread)
    if not grant.granted and grant.failed:
        # 誰にも付与できなかった場合は、成功として見せない
        await send_error_message(ctx, describe_grant(grant) + note)
        return
    await send_private_reply(
        ctx,
        create_success_embed(
            title="クラブロールメンバー追加完了",
            description=describe_grant(grant) + note,
            クラブチャンネル=club_channel.mention,
            ロール=role.name,
            追加人数=len(grant.granted),
        ),
    )
    logger.info(
        f"Added {len(grant.granted)} members to club role {role.name} "
        f"(channel: {club_channel.name}) by {ctx.user}"
    )

    if grant.granted:
        await post_channel_record(
            club_channel,
            build_members_added_embed(actor=ctx.user, role=role, members=grant.granted),
            mention_users=grant.granted,
        )


# ==================== コマンド登録 ====================


def setup(tree: app_commands.CommandTree):
    """クラブチャンネル関連のコマンドを登録する

    デコレーターの順序（重要）:
    1. @command_meta() - メタデータの登録
    2. @tree.command() - コマンドの登録
    3. @app_commands.describe() - パラメータの説明
    """

    @command_meta(
        category="クラブチャンネル管理",
        icon="🏛️",
        short_description="クラブ用のチャンネルとロールを作成",
        restrictions="• どのチャンネル・スレッドからでも実行可能",
        examples=[
            "`/create_club_channel channel_name:プログラミング部`",
            "`/create_club_channel channel_name:ロボット研究会 members:@user1 @user2`",
        ],
    )
    @tree.command(
        name="create_club_channel",
        description="新しいクラブチャンネルを作成します",
    )
    @app_commands.describe(
        channel_name="作成するクラブチャンネル名",
        members="ロールに追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
    )
    async def create_club_channel(
        ctx: discord.Interaction, channel_name: str, members: str | None = None
    ):
        await create_club_channel_impl(ctx, channel_name, members)

    @command_meta(
        category="ロール管理",
        icon="👥",
        short_description="クラブロールにメンバーを追加",
        restrictions="• 一部ロール以外のみ対象",
        examples=[
            "`/add_club_role_member members:@user1 @user2`",
            "`/add_club_role_member members:@user1 role_name:@club`",
        ],
    )
    @tree.command(
        name="add_club_role_member",
        description="クラブチャンネルに紐づくロールにメンバーを追加します",
    )
    @app_commands.describe(
        members="追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
        role_name="対象のロール（@ロール形式で指定。例: @club 省略時は実行チャンネルのロール）",
    )
    async def add_club_role_member(
        ctx: discord.Interaction, members: str, role_name: str | None = None
    ):
        await add_club_role_member_impl(ctx, members, role_name)
