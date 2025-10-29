"""イベントチャンネル設定を管理するクラス"""

import os
from dataclasses import dataclass
from logging import getLogger
from typing import Optional

import discord

logger = getLogger(__name__)


@dataclass
class EventChannelConfig:
    """イベントチャンネル関連の環境変数を保持するクラス

    このクラスはシングルトンパターンを採用し、環境変数の読み込みを
    起動時に1回だけ実行することでパフォーマンスを向上させる。

    Attributes:
        event_category_name: イベントチャンネルを作成するカテゴリー名
        archive_event_category_name: アーカイブ先のカテゴリー名
        event_request_channel_name: チャンネル作成リクエストを受け付けるチャンネル名
    """

    event_category_name: str
    archive_event_category_name: str
    event_request_channel_name: str

    # クラス変数: シングルトンインスタンス
    _instance: Optional["EventChannelConfig"] = None

    @classmethod
    def get_instance(cls) -> Optional["EventChannelConfig"]:
        """シングルトンインスタンスを取得する

        起動時に1回だけ環境変数を読み込み、以降はキャッシュされた
        インスタンスを返す。

        Returns:
            EventChannelConfig インスタンス。
            環境変数が不足している場合はNone
        """
        if cls._instance is None:
            event_category_name = os.getenv("EVENT_CATEGORY_NAME")
            archive_event_category_name = os.getenv(
                "ARCHIVE_EVENT_CATEGORY_NAME"
            )
            event_request_channel_name = os.getenv("EVENT_REQUEST_CHANNEL_NAME")

            # 環境変数のバリデーション
            missing_vars = []
            if not event_category_name:
                missing_vars.append("EVENT_CATEGORY_NAME")
            if not archive_event_category_name:
                missing_vars.append("ARCHIVE_EVENT_CATEGORY_NAME")
            if not event_request_channel_name:
                missing_vars.append("EVENT_REQUEST_CHANNEL_NAME")

            if missing_vars:
                logger.error(
                    f"Missing required environment variables: {', '.join(missing_vars)}"
                )
                logger.error(
                    "Please set the following environment variables in .env file:"
                )
                for var in missing_vars:
                    logger.error(f"  - {var}")
                return None

            # すべての環境変数が存在する場合のみインスタンスを作成
            cls._instance = cls(
                event_category_name=event_category_name,
                archive_event_category_name=archive_event_category_name,
                event_request_channel_name=event_request_channel_name,
            )

            logger.info(
                f"EventChannelConfig initialized: "
                f"event_category='{event_category_name}', "
                f"archive_category='{archive_event_category_name}', "
                f"request_channel='{event_request_channel_name}'"
            )

        return cls._instance

    @classmethod
    async def load(
        cls, ctx: discord.Interaction
    ) -> Optional["EventChannelConfig"]:
        """環境変数を読み込んでEventChannelConfigを取得する

        キャッシュされたインスタンスを返すため、複数回呼び出しても
        パフォーマンスに影響しない。

        Args:
            ctx: Discord Interaction

        Returns:
            EventChannelConfig インスタンス。
            環境変数が不足している場合はNone（エラーメッセージを表示）
        """
        config = cls.get_instance()

        if config is None:
            logger.warning(
                f"Failed to load EventChannelConfig for user {ctx.user}"
            )
            await ctx.response.send_message(
                "❌ 必要な環境変数が設定されていません。\n"
                "サーバー管理者に以下の環境変数の設定を依頼してください:\n"
                "• `EVENT_CATEGORY_NAME`\n"
                "• `ARCHIVE_EVENT_CATEGORY_NAME`\n"
                "• `EVENT_REQUEST_CHANNEL_NAME`",
                ephemeral=True,
            )
            return None

        logger.debug(f"EventChannelConfig loaded for user {ctx.user}")
        return config

    def __str__(self) -> str:
        """文字列表現を返す（デバッグ用）"""
        return (
            f"EventChannelConfig("
            f"event='{self.event_category_name}', "
            f"archive='{self.archive_event_category_name}', "
            f"request='{self.event_request_channel_name}')"
        )
