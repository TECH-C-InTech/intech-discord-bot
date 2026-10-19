"""チャンネル設定を管理するクラス"""

from dataclasses import dataclass
from logging import getLogger
import os
from typing import ClassVar, Optional

import discord

from .kinds import CLUB, EVENT, Kind

logger = getLogger(__name__)


@dataclass
class ChannelConfig:
    """チャンネル関連の環境変数を保持するクラス

    このクラスはシングルトンパターンを採用し、環境変数の読み込みを
    起動時に1回だけ実行することでパフォーマンスを向上させる。

    Attributes:
        event_category_name: イベントチャンネルを作成するカテゴリー名
        archive_event_category_name: アーカイブ先のカテゴリー名
        project_category_name: プロジェクトチャンネルを作成するカテゴリー名
        archive_project_category_name: プロジェクトのアーカイブ先カテゴリー名
        club_category_name: クラブチャンネルを作成するカテゴリー名
        archive_club_category_name: クラブのアーカイブ先カテゴリー名
    """

    event_category_name: str
    archive_event_category_name: str
    project_category_name: str
    archive_project_category_name: str
    club_category_name: str
    archive_club_category_name: str

    # クラス変数: シングルトンインスタンス
    _instance: ClassVar[Optional["ChannelConfig"]] = None

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
            values, missing_vars = _read_env()

            if missing_vars:
                logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
                for var in missing_vars:
                    logger.error(f"  - {var}")
                return None

            cls._instance = cls(**values)
            logger.info(f"ChannelConfig initialized: {cls._instance}")

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
            _, missing_vars = _read_env()
            missing_list = "\n".join(f"• `{var}`" for var in missing_vars)
            await ctx.response.send_message(
                "❌ 必要な環境変数が設定されていません。\n"
                f"サーバー管理者に以下の環境変数の設定を依頼してください:\n{missing_list}",
                ephemeral=True,
            )
            return None

        logger.debug(f"ChannelConfig loaded for user {ctx.user}")
        return config

    def category_names(self, kind: Kind) -> tuple[str, str]:
        """種類の (通常のカテゴリ名, アーカイブカテゴリ名) を返す"""
        if kind is CLUB:
            return self.club_category_name, self.archive_club_category_name
        if kind is EVENT:
            return self.event_category_name, self.archive_event_category_name
        return self.project_category_name, self.archive_project_category_name

    def __str__(self) -> str:
        """文字列表現を返す（デバッグ用）"""
        return (
            f"ChannelConfig("
            f"event='{self.event_category_name}', "
            f"archive_event='{self.archive_event_category_name}', "
            f"project='{self.project_category_name}', "
            f"archive_project='{self.archive_project_category_name}', "
            f"club='{self.club_category_name}', "
            f"archive_club='{self.archive_club_category_name}')"
        )


# 属性名と環境変数名の対応。すべて必須
ENV_VARS = {
    "event_category_name": "EVENT_CATEGORY_NAME",
    "archive_event_category_name": "ARCHIVE_EVENT_CATEGORY_NAME",
    "project_category_name": "PROJECT_CATEGORY_NAME",
    "archive_project_category_name": "ARCHIVE_PROJECT_CATEGORY_NAME",
    "club_category_name": "CLUB_CATEGORY_NAME",
    "archive_club_category_name": "ARCHIVE_CLUB_CATEGORY_NAME",
}


def _read_env() -> tuple[dict[str, str], list[str]]:
    """環境変数を読み込み、(属性名→値, 不足している環境変数名) を返す"""
    values: dict[str, str] = {}
    missing_vars: list[str] = []
    for attr, env_var in ENV_VARS.items():
        value = os.getenv(env_var)
        if value:
            values[attr] = value
        else:
            missing_vars.append(env_var)
    return values, missing_vars
