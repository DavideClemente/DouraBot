import settings
import mysql.connector
import discord
from discord.ext import commands
import sys
import os
from database import DatabaseManager
from logic.images import create_welcome_image, get_image, get_image_db
from logic.users import insert_user, get_next_user_number
logger = settings.get_logger()


class Client(commands.Bot):
    def __init__(self):
        self.logger = logger
        self.cogsFolder = settings.COGS_PATH
        self.db = DatabaseManager().create_pool()
        self.db = DatabaseManager().get_connection()
        self.setup_db()
        super().__init__(command_prefix=commands.when_mentioned_or(
            '??'), intents=discord.Intents().all())

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

    async def on_member_join(self, member: discord.Member):
        user_number = get_next_user_number(DatabaseManager().get_connection())
        self.logger.info(
            f'User number {user_number} assigned to {member.display_name}')
        insert_user(DatabaseManager().get_connection(),
                    member.id, member.display_name, user_number)
        avatar = member.avatar.url
        avatar_img = get_image(avatar)
        avatar_img = avatar_img.resize((150, 150))
        bck_image = get_image_db(
            DatabaseManager().get_connection(), 'background_welcome')

        result = create_welcome_image(
            member.display_name, user_number, avatar_img, bck_image)
        file = discord.File(result, filename='image.jpg')

        await self.get_channel(settings.DEV_CHANNEL).send(content=f"Olá {member.mention}, bem vindo/a ao servidor dos **DOURADINHOS**!", file=file)
        self.logger.info(f'{member.display_name} has joined the server')

    async def on_member_remove(self, member: discord.Member):
        self.logger.info(f'{member.display_name} has left the server')

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
