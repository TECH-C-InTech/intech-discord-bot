"""承認システムの設定を管理するクラス."""

from dataclasses import dataclass
from logging import getLogger
import os

logger = getLogger(__name__)


@dataclass
class ApprovalConfig:
    """承認システム関連の環境変数を保持するクラス.

    このクラスはシングルトンパターンを採用し、環境変数の読み込みを
    起動時に1回だけ実行することでパフォーマンスを向上させる。

    Attributes:
        approver_role_name: 承認権限を持つロール名
    """

    approver_role_name: str

    # クラス変数: シングルトンインスタンス
    _instance: "ApprovalConfig | None" = None

    @classmethod
    def get_instance(cls) -> "ApprovalConfig":
        """シングルトンインスタンスを取得する.

        起動時に1回だけ環境変数を読み込み、以降はキャッシュされた
        インスタンスを返す。

        Returns:
            ApprovalConfig インスタンス。
            環境変数が設定されていない場合はデフォルト値（"Administrator"）を使用
        """
        if cls._instance is None:
            approver_role_name = os.getenv("APPROVER_ROLE_NAME", "Administrator")

            cls._instance = cls(approver_role_name=approver_role_name)

            logger.info(f"ApprovalConfig initialized: approver_role='{approver_role_name}'")

        return cls._instance

    def __str__(self) -> str:
        """文字列表現を返す（デバッグ用）."""
        return f"ApprovalConfig(approver_role='{self.approver_role_name}')"
