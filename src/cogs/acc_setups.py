import discord
import settings
from discord.ext import commands
from database import DatabaseManager
from discord.ui import View, Button
from logic.utilities import get_persistent_message, insert_persistent_message
from discord import ButtonStyle
from cogs.configs import get_config_value


class ButtonsView(View):
    def __init__(self):
        super().__init__()
        self.add_item(Button(style=ButtonStyle.link, label='Setups',
                             url=settings.CARS_LINK, emoji='🔧'))
        self.add_item(Button(style=ButtonStyle.link, label='Jardier',
                             url=settings.TRACKS_LINK, emoji='🏁'))


class Setups(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger

    @commands.Cog.listener()
    async def on_ready(self):
        with DatabaseManager().get_connection() as conn:
            channel = self.client.get_channel(
                get_config_value("ACC_SETUPS_MSG_CHANNEL"))
            message = get_persistent_message(conn, "acc_setups_message")
            if message is None:
                insert_persistent_message(conn, "acc_setups_message")
                with open('assets/acc_cover.jpg', 'rb') as file:
                    await channel.send("**Assetto Corsa Competizione Setups**",
                                       file=discord.File(file),
                                       view=ButtonsView())
            else:
                self.logger.info("Setups message already exists")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Setups(client))
