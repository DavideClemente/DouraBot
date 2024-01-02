import discord
import mysql.connector
from discord.ext import commands, tasks
from discord import app_commands
from settings import *
from datetime import datetime
from logic.utilities import convert_to_datetime, is_role_allowed
from database import DatabaseManager


class Birthday(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = get_logger()
        self.db = DatabaseManager().get_connection()
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.stop()

    def create_embed(self, user: discord.User):
        embed = discord.Embed(
            title='🎉 Happy birthday 🎉', description="Hope your day is packed with good times, great company, and some well-deserved relaxation. Here's to another year of epic Discord adventures and awesome moments. Cheers! 🥳🎈",
            color=discord.Color.from_str(DOURADINHOS_COLOR))
        embed.set_author(name="DouraBot")
        embed.set_image(url=user.avatar.url)
        embed.set_thumbnail(
            url=DOURADINHOS_IMAGE)
        return embed

    @tasks.loop(hours=24)
    # @app_commands.command(name='check_birthdays', description='add someones birthday')
    async def check_birthdays(self):
        channel = self.client.get_channel(DEV_CHANNEL)
        today_date = datetime.utcnow().strftime("%m-%d")
        with self.db.cursor() as cursor:
            cursor.execute(
                'SELECT USER_ID, BIRTH_DATE FROM BIRTHDAYS WHERE BIRTH_DATE = %s', (today_date,))
            birthdays = cursor.fetchall()
            for userId, _ in birthdays:
                discord_user: discord.User = await self.client.fetch_user(
                    userId)

                msg = await channel.send(embed=self.create_embed(discord_user))
                await msg.add_reaction('💖')
                await msg.add_reaction('🎉')

    @app_commands.command(name='add_birthday', description="Add someone's birth so that DouraBot can wish him/her a happy birthday")
    async def add_birthday(self, itr: discord.Interaction, who: discord.Member, birthday: str):
        """Add someone's birth so that DouraBot can wish him/her a happy birthday

        Args:
            itr (discord.Interaction): _description_
            who (discord.Member): Person to add birthday
            birthday (str): Birthday date in the form of 'mm-dd' (eg.03-25)
        """
        await itr.response.defer()
        converted_birthday_date = datetime(9999, 1, 1)
        try:
            converted_birthday_date = convert_to_datetime(
                birthday).strftime("%m-%d")
        except ValueError as ex:
            await itr.followup.send(ex, ephemeral=True)
        try:
            with self.db.cursor() as cursor:
                cursor.execute('INSERT INTO BIRTHDAYS VALUES(%s,%s,%s)',
                               (who.id, who.display_name, converted_birthday_date,))
                self.db.commit()
            self.logger.info(f"Registered {who.name}'s birthday")
            await itr.followup.send(f"Registered {who.display_name}'s birthday", ephemeral=True)
        except mysql.connector.IntegrityError:
            await itr.followup.send(f"{who.display_name}'s birthday already exists. Use /edit_birthday if you want to change it", ephemeral=True)
        except Exception as e:
            await itr.followup.send(f'Error while adding birthday - {e}', ephemeral=True)

    @app_commands.command(name='edit_birthday', description="Edit someone's birthday date")
    async def edit_birthday(self, itr: discord.Interaction, who: discord.Member, new_birthday: str):
        """Edit someone's birthday date

        Args:
            itr (discord.Interaction): _description_
            who (discord.Member): Person to edit birthday
            newBirthday (str): New birthday
        """
        try:
            with self.db.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM BIRTHDAYS WHERE USER_ID = %s", (who.id,))
                birthday = cursor.fetchone()
                if birthday is None:
                    await itr.response.send_message(f'No birthday registered for {who.display_name}')
                else:
                    converted_birthday_date = convert_to_datetime(
                        new_birthday).strftime("%m-%d")
                    cursor.execute("UPDATE BIRTHDAYS SET BIRTH_DATE = %s WHERE USER_ID = %s",
                                   (converted_birthday_date, who.id,))
                    self.db.commit()
                    await itr.response.send_message(f"Edited {who.display_name}'s birthday")
        except Exception as e:
            await itr.response.send(f'Error while editing birthday - {e}', ephemeral=True)

    # @app_commands.command(name='list_birthdays', description="List birthdays in db")
    # @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DOURADINHO_MESTRE'], ROLES['DEV'])
    # async def list_birthdays(self, itr: discord.Interaction):
    #     await itr.response.defer()
    #     try:
    #         with self.db.cursor() as cursor:
    #             cursor.execute(
    #                 "SELECT * FROM BIRTHDAYS;")
    #             birthdays = cursor.fetchall()
    #             if len(birthdays) == 0:
    #                 await itr.followup.send('No birthdays found!')
    #             else:
    #                 ids, names, dates = zip(*birthdays)
    #                 await itr.followup.send("\n".join([f"{value1} - {value2} - {value3}" for value1, value2, value3 in zip(ids, names, dates)]))
    #     except Exception as e:
    #         await itr.followup.send(f'Error while fetching birthday - {e}', ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Birthday(client))
