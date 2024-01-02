import settings
import mysql.connector
import discord
from discord.ext import commands
import sys
import os
from database import DatabaseManager
logger = settings.get_logger()


class Client(commands.Bot):
    def __init__(self):
        self.logger = logger
        self.cogsFolder = settings.COGS_PATH
        self.db = DatabaseManager().connect()
        self.db = DatabaseManager().get_connection()
        self.setup_db()
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
            if filename[-3:] != '.py':
                continue
            self.logger.info(f'Loaded {filename} cog')
            await self.load_extension(f'cogs.{filename[:-3]}')

    async def on_disconnect(self):
        self.logger.info(f'Bot disconnected from Discord')

    async def on_connect(self):
        self.logger.info(f'Bot connected to Discord')

    def setup_db(self):
        cur = self.db.cursor()
        commands = ""
        with open(os.path.join('db', 'sql_init.sql'), 'r') as file:
            content = file.read()
            commands = content.split(';')
        for cmd in commands:
            try:
                cmd = cmd.strip()
                if len(cmd) > 0:
                    cur.execute(cmd.strip())
            except mysql.connector.DatabaseError as e:
                print(f'Skipped command, reason - {e}')
        self.db.commit()


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
    client.run(settings.DISCORD_TOKEN, log_handler=settings.get_handler())
