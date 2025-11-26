"""チャンネル設定を管理するクラス"""

from dataclasses import dataclass
from logging import getLogger
import os
from typing import Optional

import discord

logger = getLogger(__name__)


@dataclass
class ChannelConfig:
    """チャンネル関連の環境変数を保持するクラス

    このクラスはシングルトンパターンを採用し、環境変数の読み込みを
    起動時に1回だけ実行することでパフォーマンスを向上させる。

    Attributes:
        event_category_name: イベントチャンネルを作成するカテゴリー名
        archive_event_category_name: アーカイブ先のカテゴリー名
        event_request_channel_name: チャンネル作成リクエストを受け付けるチャンネル名
        project_category_name: プロジェクトチャンネルを作成するカテゴリー名
        archive_project_category_name: プロジェクトのアーカイブ先カテゴリー名
        project_request_channel_name: プロジェクト作成リクエストを受け付けるチャンネル名
        club_category_name: クラブチャンネルを作成するカテゴリー名
        clubs_request_channel_name: クラブチャンネル作成リクエストを受け付けるチャンネル名
    """

    event_category_name: str
    archive_event_category_name: str
    event_request_channel_name: str
    project_category_name: str
    archive_project_category_name: str
    project_request_channel_name: str
    club_category_name: str
    clubs_request_channel_name: str

    # クラス変数: シングルトンインスタンス
    _instance: Optional["ChannelConfig"] = None

    @classmethod
    def get_instance(cls) -> Optional["ChannelConfig"]:
        """シングルトンインスタンスを取得する

        起動時に1回だけ環境変数を読み込み、以降はキャッシュされた
        インスタンスを返す。

        Returns:
            ChannelConfig インスタンス。
            環境変数が不足している場合はNone
        """
        if cls._instance is None:
            event_category_name = os.getenv("EVENT_CATEGORY_NAME")
            archive_event_category_name = os.getenv("ARCHIVE_EVENT_CATEGORY_NAME")
            event_request_channel_name = os.getenv("EVENT_REQUEST_CHANNEL_NAME")
            project_category_name = os.getenv("PROJECT_CATEGORY_NAME")
            archive_project_category_name = os.getenv("ARCHIVE_PROJECT_CATEGORY_NAME")
            project_request_channel_name = os.getenv("PROJECT_REQUEST_CHANNEL_NAME")
            club_category_name = os.getenv("CLUB_CATEGORY_NAME")
            clubs_request_channel_name = os.getenv("CLUBS_REQUEST_CHANNEL_NAME")

            # 環境変数のバリデーション
            missing_vars = []
            if not event_category_name:
                missing_vars.append("EVENT_CATEGORY_NAME")
            if not archive_event_category_name:
                missing_vars.append("ARCHIVE_EVENT_CATEGORY_NAME")
            if not event_request_channel_name:
                missing_vars.append("EVENT_REQUEST_CHANNEL_NAME")
            if not project_category_name:
                missing_vars.append("PROJECT_CATEGORY_NAME")
            if not archive_project_category_name:
                missing_vars.append("ARCHIVE_PROJECT_CATEGORY_NAME")
            if not project_request_channel_name:
                missing_vars.append("PROJECT_REQUEST_CHANNEL_NAME")
            if not club_category_name:
                missing_vars.append("CLUB_CATEGORY_NAME")
            if not clubs_request_channel_name:
                missing_vars.append("CLUBS_REQUEST_CHANNEL_NAME")

            if missing_vars:
                logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
                logger.error("Please set the following environment variables in .env file:")
                for var in missing_vars:
                    logger.error(f"  - {var}")
                return None

            # すべての環境変数が存在する場合のみインスタンスを作成
            # mypy: None チェックは上で行われているのでここでは安全
            assert event_category_name is not None
            assert archive_event_category_name is not None
            assert event_request_channel_name is not None
            assert project_category_name is not None
            assert archive_project_category_name is not None
            assert project_request_channel_name is not None
            assert club_category_name is not None
            assert clubs_request_channel_name is not None
            cls._instance = cls(
                event_category_name=event_category_name,
                archive_event_category_name=archive_event_category_name,
                event_request_channel_name=event_request_channel_name,
                project_category_name=project_category_name,
                archive_project_category_name=archive_project_category_name,
                project_request_channel_name=project_request_channel_name,
                club_category_name=club_category_name,
                clubs_request_channel_name=clubs_request_channel_name,
            )

            logger.info(
                f"ChannelConfig initialized: "
                f"event_category='{event_category_name}', "
                f"archive_event_category='{archive_event_category_name}', "
                f"event_request_channel='{event_request_channel_name}', "
                f"project_category='{project_category_name}', "
                f"archive_project_category='{archive_project_category_name}', "
                f"project_request_channel='{project_request_channel_name}', "
                f"club_category='{club_category_name}', "
                f"clubs_request_channel='{clubs_request_channel_name}'"
            )

        return cls._instance

    @classmethod
    async def load(cls, ctx: discord.Interaction) -> Optional["ChannelConfig"]:
        """環境変数を読み込んでChannelConfigを取得する

        キャッシュされたインスタンスを返すため、複数回呼び出しても
        パフォーマンスに影響しない。

        Args:
            ctx: Discord Interaction

        Returns:
            ChannelConfig インスタンス。
            環境変数が不足している場合はNone（エラーメッセージを表示）
        """
        config = cls.get_instance()

        if config is None:
            logger.warning(f"Failed to load ChannelConfig for user {ctx.user}")
            await ctx.response.send_message(
                "❌ 必要な環境変数が設定されていません。\n"
                "サーバー管理者に以下の環境変数の設定を依頼してください:\n"
                "• `EVENT_CATEGORY_NAME`\n"
                "• `ARCHIVE_EVENT_CATEGORY_NAME`\n"
                "• `EVENT_REQUEST_CHANNEL_NAME`\n"
                "• `PROJECT_CATEGORY_NAME`\n"
                "• `ARCHIVE_PROJECT_CATEGORY_NAME`\n"
                "• `PROJECT_REQUEST_CHANNEL_NAME`\n"
                "• `CLUB_CATEGORY_NAME`\n"
                "• `CLUBS_REQUEST_CHANNEL_NAME`",
                ephemeral=True,
            )
            return None

        logger.debug(f"ChannelConfig loaded for user {ctx.user}")
        return config

    def __str__(self) -> str:
        """文字列表現を返す（デバッグ用）"""
        return (
            f"ChannelConfig("
            f"event='{self.event_category_name}', "
            f"archive_event='{self.archive_event_category_name}', "
            f"event_request='{self.event_request_channel_name}', "
            f"project='{self.project_category_name}', "
            f"archive_project='{self.archive_project_category_name}', "
            f"project_request='{self.project_request_channel_name}', "
            f"club='{self.club_category_name}', "
            f"clubs_request='{self.clubs_request_channel_name}')"
        )
