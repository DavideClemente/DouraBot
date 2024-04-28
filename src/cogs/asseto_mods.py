from email.mime import image
from io import BytesIO
import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import ROLES
from discord.ui import View, Button
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


class mods(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.client.get_channel(settings.MODS_CHANNEL)
        with open('assets/asseto_cover.jpg', 'rb') as file:
            await channel.send("**Asseto Corsa Mods**",
                               file=discord.File(file),
                               view=MyView())


async def setup(client: commands.Bot) -> None:
    await client.add_cog(mods(client))
