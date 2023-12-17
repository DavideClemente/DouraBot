import settings
import discord
from discord.ext import commands
import sys
import os
from sqlite_database import Database, text, integer
import sqlite3
logger = settings.get_logger()


class Client(commands.Bot):
    def __init__(self):
        self.logger = logger
        self.cogsFolder = settings.COGS_PATH
        self.db = sqlite3.connect(settings.DB_FILE_PATH)
        # self.db = Database(settings.DB_FILE_PATH)
        self.setup_db()
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

    async def on_disconnect(self):
        self.logger.info(f'Bot disconnected from Discord')
        self.db.close()

    async def on_connect(self):
        self.logger.info(f'Bot connected to Discord')
        self.db = Database(settings.DB_FILE_PATH)

    def setup_db(self):
        try:
            with self.db:
                self.db.execute(
                    'CREATE TABLE BIRTHDAYS(USER_ID INTEGER PRIMARY KEY, USERNAME TEXT NOT NULL, BIRTH_DATE TEXT NOT NULL)')
            # cur = self.db.cursor()
            # cur.execute(
            #     'CREATE TABLE BIRTHDAYS(USER_ID INTEGER PRIMARY KEY, USERNAME TEXT NOT NULL, BIRTH_DATE TEXT NOT NULL)')
        except Exception as e:
            self.logger.info(e)


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception",
                 exc_info=(exc_type, exc_value, exc_traceback))


# sys.excepthook = log_unhandled_exception

if __name__ == '__main__':
    client = Client()
    client.run(settings.DISCORD_TOKEN, root_logger=True)
