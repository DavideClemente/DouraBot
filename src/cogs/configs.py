import discord
from websockets import Data
from database import DatabaseManager
import settings
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, Select, View
from settings import ROLES
from logic.utilities import is_role_allowed

options = []
with DatabaseManager().get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT KEY_NAME, DESCRIPTION FROM CONFIGS")
    options = [discord.SelectOption(
        label=key_name, value=key_name, description=description) for key_name, description in cursor.fetchall()]


class ConfigView(View):
    def __init__(self):
        super().__init__()

    @discord.ui.select(
        cls=Select,
        placeholder="Select a config to change",
        options=options,
        row=1
    )
    async def select_callback(self, interaction: discord.Interaction, select: Select):
        return await interaction.response.defer()


class Configs(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger
        self.options = []

    @app_commands.command(name='change_config', description="Change a config value in the bot")
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DOURADINHO_MESTRE'], ROLES['DEV'])
    async def change_config(self, itr: discord.Interaction):
        """Change a config value in the bot

        Args:
            itr (discord.Interaction): _description_
        """
        view = ConfigView()
        await itr.response.send_message("Select a config to change", view=view, ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Configs(client))
