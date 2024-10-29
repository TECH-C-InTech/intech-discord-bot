from logging import getLogger
import os

import discord
from dotenv import load_dotenv

logger = getLogger(__name__)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

CLIENT = discord.Client(intents=intents)

@CLIENT.event
async def on_ready():
    print(f'We have logged in as {CLIENT.user}')

@CLIENT.event
async def on_message(message: discord.Message):
    if message.author == CLIENT.user:
        return

    if message.content.startswith('!hello'):
        await message.channel.send('Hello!')

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token is None:
        raise EnvironmentError("DISCORD_BOT_TOKEN is not set")

    CLIENT.run(token)
