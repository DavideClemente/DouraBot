import discord
from database import DatabaseManager
import settings
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View
from settings import ROLES
from logic.utilities import is_role_allowed

options = []
with DatabaseManager().get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT KEY_NAME, DESCRIPTION, TYPE FROM CONFIGS")
    options = [discord.SelectOption(
        label=key_name, value=f"{key_name}|{type}", description=description) for key_name, description, type in cursor.fetchall()]


class ChannelSelect(Select):
    def __init__(self, config_key, new_options):
        super().__init__()
        self.config_key = config_key
        self.options = new_options

    async def callback(self, interaction: discord.Interaction):
        channel_id, channel_name = self.values[0].split('|')
        try:
            save_config(self.config_key, channel_id, channel_name)
            return await interaction.response.send_message("Config Updated", ephemeral=True)
        except Exception as e:
            return await interaction.response.send_message(f"Error: {e}", ephemeral=True)


class ChannelView(View):
    def __init__(self, key_name, new_options):
        super().__init__()
        self.add_item(ChannelSelect(key_name, new_options))


class ConfigView(View):
    def __init__(self, client: commands.Bot):
        self.client = client
        super().__init__()

    @discord.ui.select(
        cls=Select,
        placeholder="Select a config to change",
        options=options,
        row=1
    )
    async def select_callback(self, interaction: discord.Interaction, select: Select):
        key_name, type = select.values[0].split('|')
        if (type == 'CHANNEL'):
            new_options = [discord.SelectOption(
                label=channel.name, value=f'{channel.id}|{channel.name}') for channel in interaction.guild.channels
                if channel.type == discord.ChannelType.text]
            return await interaction.response.send_message(view=ChannelView(key_name, new_options), ephemeral=True)
        if (type == 'ROLE'):
            return await interaction.response.send_message("New ROle", ephemeral=True)


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
        view = ConfigView(self.client)
        await itr.response.send_message("Select a config to change", view=view, ephemeral=True)

    @app_commands.command(name='get_config', description="Get a config value in the bot")
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DOURADINHO_MESTRE'], ROLES['DEV'])
    async def get_config(self, itr: discord.Interaction, key_name: str):
        """Get a config value in the bot

        Args:
            itr (discord.Interaction): _description_
        """
        await itr.response.defer()
        await itr.followup.send(content=f'⚙️ {key_name.upper()} => {get_config(key_name.upper())} ⚙️', ephemeral=True)


def save_config(key_name, value, description):
    with DatabaseManager().get_connection() as conn:
        cursor = conn.cursor()
        query = "UPDATE CONFIGS SET VALUE = %s, DESCRIPTION = %s WHERE KEY_NAME = %s"
        params = (value, description, key_name)
        cursor.execute(query, params)
        conn.commit()


def get_config(key_name):
    with DatabaseManager().get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT VALUE FROM CONFIGS WHERE KEY_NAME = %s"
        params = (key_name,)
        cursor.execute(query, params)
        return cursor.fetchall()[0][0]


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Configs(client))
