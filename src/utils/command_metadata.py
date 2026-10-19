"""コマンドメタデータ管理"""

from typing import Optional


class CommandMetadata:
    """コマンドの追加メタデータを保持するクラス"""

    def __init__(
        self,
        category: str,
        icon: str = "📝",
        short_description: Optional[str] = None,
        restrictions: Optional[str] = None,
        examples: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ):
        """
        Args:
            category: コマンドのカテゴリー（例: "イベントチャンネル管理"）
            icon: カテゴリーのアイコン（絵文字）
            short_description: /helpで表示される短い説明
            restrictions: 実行制限の説明
            examples: 使用例のリスト
            notes: 追加の注意事項
        """
        self.category = category
        self.icon = icon
        self.short_description = short_description
        self.restrictions = restrictions
        self.examples = examples or []
        self.notes = notes


# グローバルなメタデータレジストリ
_COMMAND_METADATA: dict[str, CommandMetadata] = {}


def register_command_metadata(command_name: str, metadata: CommandMetadata):
    """コマンドのメタデータを登録する"""
    _COMMAND_METADATA[command_name] = metadata


def get_command_metadata(command_name: str) -> Optional[CommandMetadata]:
    """コマンドのメタデータを取得する"""
    return _COMMAND_METADATA.get(command_name)


def get_all_metadata() -> dict[str, CommandMetadata]:
    """全てのコマンドメタデータを取得する"""
    return _COMMAND_METADATA.copy()


def command_meta(
    category: str,
    icon: str = "📝",
    short_description: Optional[str] = None,
    restrictions: Optional[str] = None,
    examples: Optional[list[str]] = None,
    notes: Optional[str] = None,
):
    """
    コマンド関数にメタデータを付与するデコレーター

    重要: このデコレーターは@tree.commandの前か関数定義の直前に配置してください。

    使用例:
        @command_meta(
            category="イベントチャンネル管理",
            icon="📅",
            short_description="イベント用のチャンネルを作成",
            restrictions="• channel_name省略時はイベントカテゴリー内で実行",
            examples=[
                "/create_channel category:イベント channel_name:ハッカソン",
                "/create_channel category:イベント channel_name:勉強会 members:@user1 @user2"
            ]
        )
        @tree.command(name="create_channel", ...)
        @app_commands.describe(...)
        async def create_channel_cmd(ctx, ...):
            ...
    """

    def decorator(func):
        # @tree.commandが先に適用されている場合、Commandオブジェクトになっている
        if hasattr(func, "name"):
            # discord.app_commands.Commandオブジェクトの場合
            command_name = func.name
        else:
            # 通常の関数の場合（@tree.commandより先に適用された場合）
            command_name = func.__name__.replace("_cmd", "")

        metadata = CommandMetadata(
            category=category,
            icon=icon,
            short_description=short_description,
            restrictions=restrictions,
            examples=examples,
            notes=notes,
        )

        register_command_metadata(command_name, metadata)
        return func

    return decorator
