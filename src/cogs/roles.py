import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import ROLES
from logic.utilities import is_role_allowed


class Roles(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger

    def create_embed(self):
        embed = discord.Embed(title="Game Roles",
                              description="Customiza o teu perfil e escolhe os roles que quiseres de acordo com os teus jogos preferidos.",
                              color=discord.Color.from_str(settings.DOURADINHOS_COLOR))
        embed.set_author(name="Douradinhos",
                         icon_url=settings.DOURADINHOS_AVATAR)

        return embed

    @app_commands.command(name='role_message', description="give roles")
    async def role_message(self, itr: discord.Interaction):
        embed = self.create_embed()
        await itr.response.send_message(embed=embed)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Roles(client))
