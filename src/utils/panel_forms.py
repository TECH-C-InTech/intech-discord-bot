"""パネルのボタンから開くフォーム（モーダル）"""

import discord

from .channel_actions import add_participants, archive, create, remove_participants
from .channel_config import ChannelConfig
from .kinds import CLUB, EVENT, PROJECT, Kind
from .linking import (
    Linked,
    NotLinked,
    collect_kind_categories,
    explain_not_linked,
    link_channel,
)
from .message_utils import send_error_message
from .panel import RESTORE_ON_POST

# 名前の入力欄に、入力前に出す例
NAME_EXAMPLES = {CLUB.key: "ラーメン", EVENT.key: "おでん会", PROJECT.key: "ハッカソン"}

# Discordのメンバー選択で選べる最大の人数
MAX_SELECTED_MEMBERS = 25


def _members(select: discord.ui.UserSelect) -> list[discord.Member]:
    # サーバーの中のフォームでは、選ばれた人はMemberで届く
    return [user for user in select.values if isinstance(user, discord.Member)]


class CreateForm(discord.ui.Modal):
    """作るフォーム。名前と、立てた人のほかの参加者を選ぶ"""

    def __init__(self, config: ChannelConfig, kind: Kind, *, next_number: str) -> None:
        super().__init__(title=f"{kind.label}を作る")
        self.config = config
        self.kind = kind
        self.name: discord.ui.TextInput = discord.ui.TextInput(
            placeholder=f"例: {NAME_EXAMPLES[kind.key]}", max_length=90
        )
        self.others: discord.ui.UserSelect = discord.ui.UserSelect(
            min_values=0, max_values=MAX_SELECTED_MEMBERS, required=False
        )
        # Discordのフォームは入力に応じて表示を変えられないので、番号は開いた時点の見込みを出す
        self.add_item(
            discord.ui.Label(
                text=f"{kind.label}名",
                description=f"番号（{next_number} など）は自動で付きます",
                component=self.name,
            )
        )
        self.add_item(discord.ui.Label(text="他の参加者（任意）", component=self.others))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await create(interaction, self.config, self.kind, self.name.value, _members(self.others))


class ParticipantsForm(discord.ui.Modal):
    """参加者を追加・外すフォーム。1人以上選ぶ"""

    def __init__(self, config: ChannelConfig, linked: Linked, *, removing: bool) -> None:
        super().__init__(title="参加者を外す" if removing else "参加者を追加")
        self.config = config
        self.linked = linked
        self.removing = removing
        self.people: discord.ui.UserSelect = discord.ui.UserSelect(
            min_values=1, max_values=MAX_SELECTED_MEMBERS, required=True
        )
        where = (
            f"#{linked.channel.name} から外します"
            if removing
            else f"#{linked.channel.name} に追加します"
        )
        self.add_item(
            discord.ui.Label(
                text="外す人" if removing else "追加する人",
                description=where,
                component=self.people,
            )
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # フォームを開いている間にアーカイブなどされていることがあるので、送った時点で紐づけ直す
        guild = interaction.guild
        assert guild is not None
        categories, missing = collect_kind_categories(guild.categories, self.config.category_names)
        linked = link_channel(self.linked.channel, guild.roles, categories)
        if isinstance(linked, NotLinked):
            await send_error_message(interaction, explain_not_linked(linked, missing))
            return
        members = _members(self.people)
        if self.removing:
            await remove_participants(interaction, linked, members)
        else:
            await add_participants(interaction, linked, members)


# Discordのフォームのタイトルの上限
MAX_FORM_TITLE = 45


class ArchiveForm(discord.ui.Modal):
    """アーカイブの確認。押した本人にだけ出る"""

    def __init__(self, config: ChannelConfig, channel: discord.TextChannel) -> None:
        suffix = " をアーカイブ"
        name = f"#{channel.name}"
        if len(name) + len(suffix) > MAX_FORM_TITLE:
            name = name[: MAX_FORM_TITLE - len(suffix) - 1] + "…"
        super().__init__(title=name + suffix)
        self.config = config
        self.channel = channel
        # フォームの決定ボタンは「送信」で固定なので、押すと何が起きるかを書く
        self.add_item(
            discord.ui.TextDisplay(
                f"アーカイブ中も、{RESTORE_ON_POST}。\n「送信」を押すとアーカイブします。"
            )
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await archive(interaction, self.config, self.channel)
