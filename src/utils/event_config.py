"""イベントチャンネル設定を管理するクラス"""

import os
from dataclasses import dataclass
from typing import Optional

import discord


@dataclass
class EventChannelConfig:
    """イベントチャンネル関連の環境変数を保持するクラス"""

    event_category_name: str
    archive_event_category_name: str
    event_request_channel_name: str

    _instance: Optional["EventChannelConfig"] = None

    @classmethod
    def get_instance(cls) -> Optional["EventChannelConfig"]:
        """
        シングルトンインスタンスを取得する（起動時に1回だけ環境変数を読み込む）

        Returns:
            EventChannelConfig インスタンス。環境変数が不足している場合はNone
        """
        if cls._instance is None:
            event_category_name = os.getenv("EVENT_CATEGORY_NAME")
            archive_event_category_name = os.getenv("ARCHIVE_EVENT_CATEGORY_NAME")
            event_request_channel_name = os.getenv("EVENT_REQUEST_CHANNEL_NAME")

            # すべての環境変数が存在する場合のみインスタンスを作成
            if (
                event_category_name
                and archive_event_category_name
                and event_request_channel_name
            ):
                cls._instance = cls(
                    event_category_name=event_category_name,
                    archive_event_category_name=archive_event_category_name,
                    event_request_channel_name=event_request_channel_name,
                )

        return cls._instance

    @classmethod
    async def load(cls, ctx: discord.Interaction) -> Optional["EventChannelConfig"]:
        """
        環境変数を読み込んでEventChannelConfigを取得する（キャッシュ済み）

        Args:
            ctx: Discord Interaction

        Returns:
            EventChannelConfig インスタンス。環境変数が不足している場合はNone
        """
        config = cls.get_instance()

        if config is None:
            await ctx.response.send_message(
                "❌ 必要な環境変数が設定されていません。管理者に連絡してください。",
                ephemeral=True,
            )

        return config
