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
        approval_timeout_hours: 承認リクエストのタイムアウト時間（時間単位）
    """

    approver_role_name: str
    approval_timeout_hours: int

    # クラス変数: シングルトンインスタンス
    _instance: "ApprovalConfig | None" = None

    @classmethod
    def get_instance(cls) -> "ApprovalConfig":
        """シングルトンインスタンスを取得する.

        起動時に1回だけ環境変数を読み込み、以降はキャッシュされた
        インスタンスを返す。

        Returns:
            ApprovalConfig インスタンス。
            環境変数が設定されていない場合はデフォルト値を使用
            （approver_role_name="Administrator", approval_timeout_hours=24）
        """
        if cls._instance is None:
            approver_role_name = os.getenv("APPROVER_ROLE_NAME", "Administrator")
            approval_timeout_hours_str = os.getenv("APPROVAL_TIMEOUT_HOURS", "24")

            # タイムアウト時間のパース
            try:
                approval_timeout_hours = int(approval_timeout_hours_str)
                if approval_timeout_hours <= 0:
                    logger.warning(
                        f"APPROVAL_TIMEOUT_HOURS must be positive, got {approval_timeout_hours}. "
                        "Using default value 24."
                    )
                    approval_timeout_hours = 24
            except ValueError:
                logger.warning(
                    f"Invalid APPROVAL_TIMEOUT_HOURS value: '{approval_timeout_hours_str}'. "
                    "Using default value 24."
                )
                approval_timeout_hours = 24

            cls._instance = cls(
                approver_role_name=approver_role_name,
                approval_timeout_hours=approval_timeout_hours,
            )

            logger.info(
                f"ApprovalConfig initialized: approver_role='{approver_role_name}', "
                f"approval_timeout_hours={approval_timeout_hours}"
            )

        return cls._instance

    def __str__(self) -> str:
        """文字列表現を返す（デバッグ用）."""
        return (
            f"ApprovalConfig(approver_role='{self.approver_role_name}', "
            f"approval_timeout_hours={self.approval_timeout_hours})"
        )
