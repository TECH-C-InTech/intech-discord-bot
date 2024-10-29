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
    # :{emoji.name}: にすると、サーバー内で使えるカスタム絵文字を表示できる

    state = ""
    message = ""

    # logger.info("Diff:")
    state = "Diff:" if set(before) != set(after) else ""
    for emoji in set(after) - set(before):
        message += f"Emoji: :{emoji.name}: added\n"
        logger.info(message)

    for emoji in set(before) - set(after):
        message += f"Emoji: :{emoji.name}: removed\n"
        logger.info(message)

    # beforeにもあって、afterにもあるもの以外が変更されたもの
    state = "Changed:" if set(before) & set(after) else ""
    # logger.info("Changed:")
    for emoji in set(before) & set(after):
        if emoji in before and emoji in after:
            if before[before.index(emoji)].name != after[after.index(emoji)].name:
                message += f"Emoji: :{before[before.index(emoji)].name}: changed to :{after[after.index(emoji)].name}:\n"
                logger.info(message)

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
