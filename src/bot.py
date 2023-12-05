import settings
import discord
from discord.ext import commands
from settings import ROLES


class Client(commands.Bot):
    def __init__(self):
        self.cogsList = ['cogs.xmas', 'cogs.admin']
        self.logger = settings.get_logger()
        super().__init__(command_prefix=commands.when_mentioned_or(
            '??'), intents=discord.Intents().default())

    async def on_ready(self):
        self.logger.debug(f'User: {self.user} (ID: {self.user.id})')
        self.tree.copy_global_to(guild=settings.DISCORD_GUILD)
        synced = await self.tree.sync(guild=settings.DISCORD_GUILD)
        self.logger.info(f'Synced {len(synced)} commands')

    async def setup_hook(self):
        for ext in self.cogsList:
            await self.load_extension(ext)


if __name__ == '__main__':
    client = Client()
    client.run(settings.DISCORD_TOKEN, root_logger=True)
