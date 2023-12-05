import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import ROLES


class utils(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    def is_role_allowed(self, *roles):
        def predicate(inter: discord.Interaction):
            return any(role in [r.id for r in inter.user.roles] for role in roles)
        return app_commands.check(predicate)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(utils(client))
