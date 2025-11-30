"""統合チャンネル管理コマンド"""

from logging import getLogger
from typing import Literal

import discord
from discord import app_commands

from ..utils.approval_config import ApprovalConfig
from ..utils.approval_utils import (
    create_approval_request_embed,
    create_request_details_embed,
    has_approver_role,
)
from ..utils.channel_config import ChannelConfig
from ..utils.command_metadata import command_meta
from ..utils.message_utils import send_error_message
from ..views.approval_view import ApprovalView
from .club_channel import (
    add_club_role_member_impl,
    create_club_channel_impl,
)
from .event_channel import (
    add_event_role_member_impl,
    archive_event_channel_impl,
    create_event_channel_impl,
    restore_event_channel_impl,
)
from .project_channel import (
    add_project_role_member_impl,
    archive_project_channel_impl,
    create_project_channel_impl,
    restore_project_channel_impl,
)

logger = getLogger(__name__)


# ==================== コマンド登録 ====================


def setup(tree: app_commands.CommandTree):
    """統合チャンネル関連のコマンドを登録する

    デコレーターの順序（重要）:
    1. @command_meta() - メタデータの登録
    2. @tree.command() - コマンドの登録
    3. @require_channel() - チャンネル制限（オプション）
    4. @require_approval() - 承認ミドルウェア（オプション）
    5. @app_commands.describe() - パラメータの説明
    """

    @command_meta(
        category="チャンネル管理",
        icon="🏗️",
        short_description="カテゴリを指定してチャンネルとロールを作成",
        restrictions="• カテゴリごとに異なるリクエストチャンネルでのみ実行可能",
        examples=[
            "`/create_channel category:club channel_name:プログラミング部`",
            "`/create_channel category:event channel_name:おでん会 members:@user1 @user2`",
            "`/create_channel category:project channel_name:ハッカソン members:@user1`",
        ],
    )
    @tree.command(
        name="create_channel",
        description="カテゴリを指定して新しいチャンネルを作成します",
    )
    @app_commands.describe(
        category="チャンネルのカテゴリ（club: クラブ、event: イベント、project: プロジェクト）",
        channel_name="作成するチャンネル名",
        members="ロールに追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="クラブ (club)", value="club"),
            app_commands.Choice(name="イベント (event)", value="event"),
            app_commands.Choice(name="プロジェクト (project)", value="project"),
        ]
    )
    async def create_channel(
        ctx: discord.Interaction,
        category: Literal["club", "event", "project"],
        channel_name: str,
        members: str | None = None,
    ):
        """カテゴリに応じたチャンネルを作成する"""
        # カテゴリに応じてリクエストチャンネルの制限をチェック
        config = await ChannelConfig.load(ctx)
        if not config:
            return

        # カテゴリごとのリクエストチャンネル名を取得
        if category == "club":
            request_channel_name = config.clubs_request_channel_name
            approval_desc = "新しいクラブチャンネルを作成します"
            impl_func = create_club_channel_impl
        elif category == "event":
            request_channel_name = config.event_request_channel_name
            approval_desc = "新しいイベントチャンネルを作成します"
            impl_func = create_event_channel_impl
        elif category == "project":
            request_channel_name = config.project_request_channel_name
            approval_desc = "新しいプロジェクトチャンネルを作成します"
            impl_func = create_project_channel_impl
        else:
            await send_error_message(ctx, f"不正なカテゴリ: {category}")
            return

        # リクエストチャンネルでのみ実行可能かチェック
        if not isinstance(ctx.channel, discord.TextChannel):
            await send_error_message(ctx, "このコマンドはテキストチャンネルでのみ実行できます。")
            return

        if ctx.channel.name != request_channel_name:
            await send_error_message(
                ctx,
                f"このコマンドは `{request_channel_name}` チャンネルでのみ実行できます。",
            )
            return

        # Interactionがギルド内でない場合はエラー
        if not ctx.guild or not isinstance(ctx.user, discord.Member):
            await send_error_message(
                ctx, "このコマンドはサーバー内でのみ使用できます。", ephemeral=True
            )
            return

        # 実行者が承認ロールを持っている場合は即座に実行
        if has_approver_role(ctx.user):
            approval_config = ApprovalConfig.get_instance()
            logger.info(
                f"Command 'create_channel' (category={category}) "
                f"executed immediately by {ctx.user} "
                f"(has '{approval_config.approver_role_name}' role)"
            )
            await impl_func(ctx, channel_name, members)
            return

        # 承認リクエストを送信
        logger.info(
            f"Approval request sent for command 'create_channel' "
            f"(category={category}) by {ctx.user}"
        )

        # タイムアウト時間を取得
        approval_config = ApprovalConfig.get_instance()
        timeout_hours = approval_config.approval_timeout_hours

        # 承認リクエストEmbedを作成
        approval_embed = create_approval_request_embed(
            command_name=f"create_channel (category={category})",
            requester=ctx.user,
            timeout_hours=timeout_hours,
            description=approval_desc,
        )

        # ApprovalViewを作成
        approval_view = ApprovalView(
            command_func=impl_func,
            command_name=f"create_channel (category={category})",
            original_interaction=ctx,
            args=(channel_name, members),
            kwargs={},
            timeout_hours=timeout_hours,
        )

        # 承認権限を持つロールを取得
        approver_roles = [
            role for role in ctx.guild.roles if role.name == approval_config.approver_role_name
        ]

        # 承認権限を持つロールをメンション
        mentions = " ".join([f"<@&{role.id}>" for role in approver_roles])
        if not mentions:
            mentions = f"**「{approval_config.approver_role_name}」ロールを持つユーザー**"

        # 承認リクエストメッセージを送信
        await ctx.response.send_message(
            content=mentions,
            embed=approval_embed,
            view=approval_view,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )

        # 送信したメッセージをViewに保存（編集用）
        message = await ctx.original_response()
        approval_view.message = message

        # スレッドを作成
        auto_archive_duration: Literal[60, 1440, 4320, 10080]
        if timeout_hours <= 1:
            auto_archive_duration = 60
        elif timeout_hours <= 24:
            auto_archive_duration = 1440
        elif timeout_hours <= 72:
            auto_archive_duration = 4320
        else:
            auto_archive_duration = 10080

        try:
            thread = await message.create_thread(
                name=f"承認: create_channel ({category})",
                auto_archive_duration=auto_archive_duration,
                reason=f"Approval thread for command 'create_channel' (category={category})",
            )
            approval_view.thread = thread

            # リクエスト詳細をスレッド内に投稿
            details_embed = create_request_details_embed(
                command_name=f"create_channel (category={category})",
                args=(channel_name, members),
                kwargs={},
                description=approval_desc,
            )
            await thread.send(embed=details_embed)

            logger.info(
                f"Created approval thread '{thread.name}' (ID: {thread.id}) "
                f"for command 'create_channel' (category={category})"
            )
        except discord.HTTPException as e:
            logger.error(f"Failed to create approval thread: {e}")
            # スレッド作成に失敗しても承認フローは継続

    @command_meta(
        category="ロール管理",
        icon="👥",
        short_description="カテゴリを指定してロールにメンバーを追加",
        restrictions="• カテゴリごとに異なる制限あり",
        examples=[
            "`/add_role_members category:club members:@user1 @user2`",
            "`/add_role_members category:event members:@user1 role_name:@e001`",
            "`/add_role_members category:project members:@user1 role_name:@p001`",
        ],
    )
    @tree.command(
        name="add_role_members",
        description="カテゴリを指定してロールにメンバーを追加します",
    )
    @app_commands.describe(
        category="ロールのカテゴリ（club: クラブ、event: イベント、project: プロジェクト）",
        members="追加するメンバー（メンション形式で複数指定可能。例: @user1 @user2）",
        role_name="対象のロール（@ロール形式で指定。省略時は実行チャンネルのロール）",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="クラブ (club)", value="club"),
            app_commands.Choice(name="イベント (event)", value="event"),
            app_commands.Choice(name="プロジェクト (project)", value="project"),
        ]
    )
    async def add_role_members(
        ctx: discord.Interaction,
        category: Literal["club", "event", "project"],
        members: str,
        role_name: str | None = None,
    ):
        """カテゴリに応じたロールにメンバーを追加する"""
        if category == "club":
            await add_club_role_member_impl(ctx, members, role_name)
        elif category == "event":
            await add_event_role_member_impl(ctx, members, role_name)
        elif category == "project":
            await add_project_role_member_impl(ctx, members, role_name)
        else:
            await send_error_message(ctx, f"不正なカテゴリ: {category}")

    @command_meta(
        category="チャンネル管理",
        icon="📦",
        short_description="カテゴリを指定してチャンネルをアーカイブ",
        restrictions="• channel_name省略時はカテゴリー内で実行",
        examples=[
            "`/archive_channel category:events` (実行チャンネルをアーカイブ)",
            "`/archive_channel category:events channel_name:#e001-おでん会`",
            "`/archive_channel category:projects channel_name:#p001-ハッカソン`",
        ],
    )
    @tree.command(
        name="archive_channel",
        description="カテゴリを指定してチャンネルをアーカイブします",
    )
    @app_commands.describe(
        category="チャンネルのカテゴリ（events: イベント、projects: プロジェクト）",
        channel_name="アーカイブするチャンネル（メンション形式、省略時はコマンド実行チャンネル）",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="イベント (events)", value="events"),
            app_commands.Choice(name="プロジェクト (projects)", value="projects"),
        ]
    )
    async def archive_channel(
        ctx: discord.Interaction,
        category: Literal["events", "projects"],
        channel_name: discord.TextChannel | None = None,
    ):
        """カテゴリに応じたチャンネルをアーカイブする"""
        if category == "events":
            await archive_event_channel_impl(ctx, channel_name)
        elif category == "projects":
            await archive_project_channel_impl(ctx, channel_name)
        else:
            await send_error_message(ctx, f"不正なカテゴリ: {category}")

    @command_meta(
        category="チャンネル管理",
        icon="♻️",
        short_description="カテゴリを指定してチャンネルを復元",
        restrictions="• アーカイブカテゴリー内のチャンネルでのみ実行可能",
        examples=[
            "`/restore_channel category:events` (実行チャンネルを復元)",
            "`/restore_channel category:events channel_name:#e001-おでん会`",
            "`/restore_channel category:projects channel_name:#p001-ハッカソン`",
        ],
    )
    @tree.command(
        name="restore_channel",
        description="カテゴリを指定してアーカイブからチャンネルを復元します",
    )
    @app_commands.describe(
        category="チャンネルのカテゴリ（events: イベント、projects: プロジェクト）",
        channel_name="復元するチャンネル（メンション形式、デフォルトはコマンド実行チャンネル）",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="イベント (events)", value="events"),
            app_commands.Choice(name="プロジェクト (projects)", value="projects"),
        ]
    )
    async def restore_channel(
        ctx: discord.Interaction,
        category: Literal["events", "projects"],
        channel_name: discord.TextChannel | None = None,
    ):
        """カテゴリに応じたチャンネルを復元する"""
        if category == "events":
            await restore_event_channel_impl(ctx, channel_name)
        elif category == "projects":
            await restore_project_channel_impl(ctx, channel_name)
        else:
            await send_error_message(ctx, f"不正なカテゴリ: {category}")
