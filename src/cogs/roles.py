import discord
import settings
from discord.ext import commands
from discord import Emoji, app_commands
from settings import ROLES
from logic.utilities import is_role_allowed
from discord.ui import Button, Select, View


roles = [("ASSETO", "🏎️")]


class MyView(View):
    def __init__(self):
        super().__init__()

    @discord.ui.select(
        cls=Select,
        placeholder="Select currency to convert from",
        options=[discord.SelectOption(
            label=role[0], value=settings.ROLES[role[0]], emoji=role[1])
            for role in roles],
        row=1)
    async def select_callback(self, interaction: discord.Interaction, select: Select):
        user = interaction.user
        role = discord.utils.get(user.guild.roles, id=select.values[0])
        user.add_roles(role)
        return await interaction.response.defer()


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

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.client.get_channel(settings.DEV_CHANNEL)
        await channel.send(embed=self.create_embed(),
                           view=MyView())


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Roles(client))
