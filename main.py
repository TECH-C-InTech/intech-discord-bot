from logging import getLogger, basicConfig
import os

import discord
from dotenv import load_dotenv

logger = getLogger(__name__)
basicConfig(level="INFO")

load_dotenv()

intents = discord.Intents.default()
intents.emojis_and_stickers = True  # Required to receive on_guild_emojis_update

CLIENT = discord.Client(intents=intents)

@CLIENT.event
async def on_ready():
    print(f'We have logged in as {CLIENT.user}')

@CLIENT.event
async def on_guild_emojis_update(guild: discord.Guild, before: list[discord.Emoji], after: list[discord.Emoji]):
    # <:{emoji.name}:{emoji_id}> にすると、サーバー内で使えるカスタム絵文字を表示できる

    state = ""
    message = ""

    for emoji in set(after) - set(before):
        state = "Added:"
        message = f"Emoji: <:{emoji.name}:{emoji.id}> added"

    for emoji in set(before) - set(after):
        state = "Removed:"
        message = f"Emoji: :{emoji.name}: removed"

    # beforeにもあって、afterにもあるもの以外が変更されたもの
    for emoji in set(before) & set(after):
        if emoji in before and emoji in after:
            if before[before.index(emoji)].name != after[after.index(emoji)].name:
                state = "Renamed:"
                before_emoji = before[before.index(emoji)]
                after_emoji = after[after.index(emoji)]
                message = f"Emoji: <:{before_emoji.name}:{before_emoji.id}> renamed to :{after_emoji.name}:"

    if message != "":
        logger.info("-" * 20)
        logger.info(f"Guild: {guild.name}")
        logger.info(state)
        logger.info(message)

    # send event
    channel_name = os.getenv("EMOJI_LOG_CHANNEL_NAME")

    def send_message(channel_list: list[discord.Thread | discord.TextChannel]):
        channel = discord.utils.get(channel_list, name=channel_name)
        if channel is not None:
            return channel.send(message)
        else:
            logger.error(f"{channel_name} channel not found")
            return None

    if os.getenv("IS_DEBUG"):
        await send_message(guild.threads)
    else:
        await send_message(guild.text_channels)

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token is None:
        raise EnvironmentError("DISCORD_BOT_TOKEN is not set")

    CLIENT.run(token)
