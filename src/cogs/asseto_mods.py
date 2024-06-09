import discord
import settings
from discord.ext import commands
from database import DatabaseManager
from discord.ui import View, Button
from logic.utilities import get_persistent_message, insert_persistent_message
from discord import ButtonStyle


class LinkButton(Button):
    def __init__(self, label: str, url: str):
        super().__init__(style=ButtonStyle.link, label=label, url=url)


class MyView(View):
    def __init__(self):
        super().__init__()
        self.add_item(Button(style=ButtonStyle.link, label='Cars',
                      url=settings.CARS_LINK, emoji='🏎️'))
        self.add_item(Button(style=ButtonStyle.link, label='Tracks',
                      url=settings.TRACKS_LINK, emoji='🗺️'))
        self.add_item(Button(style=ButtonStyle.link, label='Apps',
                      url=settings.APPS_LINK, emoji='📱'))


class Mods(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger

    @commands.Cog.listener()
    async def on_ready(self):
        with DatabaseManager().get_connection() as conn:
            channel = self.client.get_channel(settings.MODS_CHANNEL)
            message = get_persistent_message(conn, "mods_message")
            if message is None:
                insert_persistent_message(conn, "mods_message")
                with open('assets/asseto_cover.jpg', 'rb') as file:
                    await channel.send("**Asseto Corsa Mods**",
                                       file=discord.File(file),
                                       view=MyView())
            else:
                self.logger.info("Mods message already exists")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Mods(client))
