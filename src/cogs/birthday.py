from typing import Any, Coroutine
import discord
import settings
from discord.ext import commands, tasks
from discord import app_commands
from settings import ROLES
import sys
from .logic.utilities import is_role_allowed
from mongo_simulator import MongoSimulator
from datetime import datetime
from cogs.logic.utilities import convert_to_datetime

logger = settings.get_logger()


class Birthday(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = logger
        self.db = MongoSimulator(
            'C:\\Users\\davide.clemente\\Documents\\Stuff\\Projects\\GitHub\\DouraBot\\db\\local_mongo.json')
        # self.db.insert_document('Davide', '2001-07-27')
        self.check_birthdays.start()

    def cog_unload(self) -> Coroutine[Any, Any, None]:
        self.check_birthdays.stop()

    @tasks.loop(seconds=10)
    async def check_birthdays(self):
        channel = self.client.get_channel(1171143985595686983)
        # today_date = datetime.utcnow().strftime('%m-%d')
        today_date = '2001-07-27'
        birthdays: list(dict) = self.db.find_documents(today_date)
        for birthday in birthdays:
            print(f'Happy birthday {birthday.get("name")}')
            # await channel.send(f'Happy birthday {birthday.get("name")}')

    @app_commands.command(name='add_birthday', description='add someones birthday')
    async def add_birthday(self, itr: discord.Interaction, who: discord.Member, birthday: str):
        await itr.response.defer()
        converted_birthday = convert_to_datetime(birthday)
        self.db.insert_document(who.name, converted_birthday)
        await itr.followup.send(f"Registered {who.name}'s birthday")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Birthday(client))
