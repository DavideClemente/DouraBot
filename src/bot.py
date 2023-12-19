import settings
import discord
from discord.ext import commands
import sys
import os
import sqlite3
from database import DatabaseManager
logger = settings.get_logger()


class Client(commands.Bot):
    def __init__(self):
        self.logger = logger
        self.cogsFolder = settings.COGS_PATH
        if settings.IS_DEV:
            self.db = DatabaseManager().connect(settings.DB_FILE_PATH)
        else:
            self.db = DatabaseManager().connect(settings.DOCKER_VOLUME_PATH)
        super().__init__(command_prefix=commands.when_mentioned_or(
            '??'), intents=discord.Intents().default())

    async def on_ready(self):
        self.logger.info(f'User: {self.user} (ID: {self.user.id})')
        self.tree.copy_global_to(guild=settings.DISCORD_GUILD)
        synced = await self.tree.sync(guild=settings.DISCORD_GUILD)
        self.logger.info(
            f'Synced {len(synced)} commands: {[s.name for s in synced]}')

    async def setup_hook(self):
        skips = []
        for filename in os.listdir(self.cogsFolder):
            cog_path = os.path.join(self.cogsFolder, filename)
            # Skip directories
            if os.path.isdir(cog_path):
                continue
            if filename[:-3] in skips:
                continue
            self.logger.info(f'Loaded {filename} cog')
            await self.load_extension(f'cogs.{filename[:-3]}')

    async def on_disconnect(self):
        self.logger.info(f'Bot disconnected from Discord')

    async def on_connect(self):
        self.logger.info(f'Bot connected to Discord')

    def setup_db(self):
        try:
            with self.db:
                self.db.execute(
                    'CREATE TABLE BIRTHDAYS(USER_ID INTEGER PRIMARY KEY, USERNAME TEXT NOT NULL, BIRTH_DATE TEXT NOT NULL)')
        except Exception as e:
            self.logger.info(e)


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception",
                 exc_info=(exc_type, exc_value, exc_traceback))


if settings.ENVIRONMENT == 'PROD':
    sys.excepthook = log_unhandled_exception

if __name__ == '__main__':
    client = Client()
    client.run(settings.DISCORD_TOKEN, root_logger=True)
