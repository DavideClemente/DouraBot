import sqlite3
import discord
import settings
from discord.ext import commands, tasks
from discord import app_commands
import settings
from local_json_db import LocalJsonDB
from datetime import datetime
from logic.utilities import convert_to_datetime
import os
from sqlite_database import Database, integer, text
from sqlite_database.operators import eq, like, between

logger = settings.get_logger()


class Birthday(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = logger
        self.db = sqlite3.connect(settings.DB_FILE_PATH)
        # self.check_birthdays.start()

    # def cog_unload(self):
    #     self.check_birthdays.stop()

    def create_embed(self, user: discord.User):
        embed = discord.Embed(
            title='🎉 Happy birthday 🎉', description="Hope your day is packed with good times, great company, and some well-deserved relaxation. Here's to another year of epic Discord adventures and awesome moments. Cheers! 🥳🎈")
        embed.set_author(name="DouraBot")
        embed.set_image(url=user.avatar.url)
        embed.set_thumbnail(
            url=settings.DOURADINHOS_IMAGE)
        return embed

    # @tasks.loop(hours=24)
    @app_commands.command(name='check_birthdays', description='add someones birthday')
    async def check_birthdays(self, itr):
        channel = self.client.get_channel(settings.DEV_CHANNEL)
        today_date = datetime.utcnow().strftime("%m-%d")
        birthdays = self.db.execute(
            'SELECT USER_ID, BIRTH_DATE FROM BIRTHDAYS WHERE BIRTH_DATE = ?', (today_date,)).fetchall()

        for userId, _ in birthdays:
            discord_user: discord.User = await self.client.fetch_user(
                userId)

            msg = await channel.send(embed=self.create_embed(discord_user))
            await msg.add_reaction('💖')
            await msg.add_reaction('🎉')

    @app_commands.command(name='add_birthday', description="add someone's birthday. Birthday should be like MM-DD")
    async def add_birthday(self, itr: discord.Interaction, who: discord.Member, birthday: str):
        await itr.response.defer()
        converted_birthday_date = datetime(9999, 1, 1)
        try:
            converted_birthday_date = convert_to_datetime(
                birthday).strftime("%m-%d")
        except ValueError as ex:
            await itr.followup.send(ex, ephemeral=True)
        try:
            with self.db:
                self.db.execute('INSERT INTO BIRTHDAYS VALUES(?,?,?)',
                                (who.id, who.display_name, converted_birthday_date))
            self.logger.info(f"Registered {who.name}'s birthday")
            await itr.followup.send(f"Registered {who.display_name}'s birthday", ephemeral=True)
        except sqlite3.IntegrityError:
            await itr.followup.send(f"{who.display_name}'s birthday already exists. Use /edit_birthday if you want to change it", ephemeral=True)
        except Exception as e:
            await itr.followup.send(f'Error while adding birthday - {e}', ephemeral=True)

    async def edit_birthday(self, itr: discord.Interaction, who: discord.Member, newBirthday: str):
        await itr.response.send_message('Not implemented yet!')

    def birthday_exists(self, userId: int):
        birthdays = self.db.table('birthdays').select(
            [eq('userId', userId)]
        )
        return birthdays is None


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Birthday(client))