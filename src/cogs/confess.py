import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import ROLES

logger = settings.get_logger()


class Confess(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = logger

    @app_commands.command(name='confess', description='confess something')
    async def confess(self, itr: discord.Interaction, msg: str):
        # Delete the invoking message
        await itr.message.message.delete()

        # Send a response and delete it immediately
        response = await itr.response.send_message(f'{msg}+(confession)')
        await response.delete()


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Confess(client))
