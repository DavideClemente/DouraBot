import settings
import discord
from discord.ext import commands
import sys
import os

logger = settings.get_logger()


class Client(commands.Bot):
    def __init__(self):
        self.cogsList = ['cogs.xmas', 'cogs.admin']
        self.logger = logger
        self.cogsFolder = os.path.join('.', 'src', 'cogs')
        super().__init__(command_prefix=commands.when_mentioned_or(
            '??'), intents=discord.Intents().default())

    async def on_ready(self):
        self.logger.info(f'User: {self.user} (ID: {self.user.id})')
        self.tree.copy_global_to(guild=settings.DISCORD_GUILD)
        synced = await self.tree.sync(guild=settings.DISCORD_GUILD)
        self.logger.info(f'Synced {len(synced)} commands')

    async def setup_hook(self):
        for filename in os.listdir(self.cogsFolder):
            cog_path = os.path.join(self.cogsFolder, filename)
            # Skip directories
            if os.path.isdir(cog_path):
                continue
            await self.load_extension(f'cogs.{filename[:-3]}')


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception",
                 exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = log_unhandled_exception

if __name__ == '__main__':
    client = Client()
    client.run(settings.DISCORD_TOKEN, root_logger=True)
