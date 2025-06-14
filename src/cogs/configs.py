import discord
from database import DatabaseManager
import settings
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View, RoleSelect
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
            update_config(self.config_key, channel_id, channel_name)
            return await interaction.response.send_message("Config Updated", ephemeral=True)
        except Exception as e:
            return await interaction.response.send_message(f"Error: {e}", ephemeral=True)


class RoleView(View):
    def __init__(self, key_name, new_options):
        super().__init__()
        self.add_item(RoleSelect(key_name, new_options))


class RoleSelect(RoleSelect):
    def __init__(self, config_key, new_options):
        super().__init__()
        self.config_key = config_key
        self.options = new_options

    async def callback(self, interaction: discord.Interaction):
        try:
            update_config(self.config_key,
                          self.values[0].id, self.values[0].name)
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
        key_name, config_type = select.values[0].split('|')
        if config_type == 'CHANNEL':
            new_options = [discord.SelectOption(
                label=channel.name, value=f'{channel.id}|{channel.name}') for channel in interaction.guild.channels
                if channel.type == discord.ChannelType.text]
            return await interaction.response.send_message(view=ChannelView(key_name, new_options), ephemeral=True)
        if config_type == 'ROLE':
            new_options = [discord.SelectOption(
                label=role.name, value=f'{role.id}|{role.name}') for role in interaction.guild.roles]
            return await interaction.response.send_message(view=RoleView(key_name, new_options), ephemeral=True)


class MyView(View):
    def __init__(self, key_name, value, description):
        self.type = None
        self.key_name = key_name
        self.value = value
        self.description = description
        super().__init__()

    @discord.ui.select(
        cls=Select,
        placeholder="Select a type",
        options=[
            discord.SelectOption(label='Channel', value='CHANNEL'),
            discord.SelectOption(label='Role', value='ROLE'),
            discord.SelectOption(label='User', value='USER'),
            discord.SelectOption(label='General', value='GENERAL')
        ],
        row=1
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.type = select.values[0]
        return await interaction.response.defer()

    @discord.ui.button(
        label="Add",
        row=2,
        style=discord.ButtonStyle.primary,
    )
    async def add(self, interaction: discord.Interaction, _):
        if self.type is None:
            return await interaction.response.send_message("Please select a type", ephemeral=True)
        try:
            save_config(self.key_name, self.value, self.description, self.type)
            return await interaction.response.send_message("Config Added", ephemeral=True)
        except:
            return await interaction.response.send_message("Error while adding config", ephemeral=True)


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

    @app_commands.command(name='get_configs', description="Get all config values in the bot")
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DOURADINHO_MESTRE'], ROLES['DEV'])
    async def get_configs(self, itr: discord.Interaction):
        """Get a config value in the bot

        Args:
            itr (discord.Interaction): _description_
        """
        await itr.response.defer()
        configs = get_configs()
        config_message = "```"
        for key, _, description in configs:
            config_message += f"{key} => {description}\n"
        config_message += "```"
        await itr.followup.send(content=config_message, ephemeral=True)

    @app_commands.command(name='add_config', description="ADD a config value to the bot")
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DOURADINHO_MESTRE'], ROLES['DEV'])
    async def add_config(self, itr: discord.Interaction, key_name: str, value: str, description: str):
        """Get a config value in the bot

        Args:
            itr (discord.Interaction): _description_
            :param itr:
            :param description: Config description
            :param value: Config value
            :param key_name: Config key name
        """
        await itr.response.defer()
        view = MyView(key_name, value, description)
        await itr.followup.send("Select a type", view=view, ephemeral=True)


def save_config(key_name, value, description, conf_type):
    with DatabaseManager().get_connection() as l_conn:
        l_cursor = l_conn.cursor()
        query = "INSERT INTO CONFIGS (KEY_NAME, VALUE, DESCRIPTION, TYPE) VALUES (%s, %s, %s, %s)"
        params = (key_name, value, description, conf_type)
        l_cursor.execute(query, params)
        l_conn.commit()


def update_config(key_name, value, description):
    with DatabaseManager().get_connection() as l_conn:
        l_cursor = l_conn.cursor()
        query = "UPDATE CONFIGS SET VALUE = %s, DESCRIPTION = %s WHERE KEY_NAME = %s"
        params = (value, description, key_name)
        l_cursor.execute(query, params)
        l_conn.commit()


def get_config(key_name):
    with DatabaseManager().get_connection() as l_conn:
        l_cursor = l_conn.cursor()
        query = "SELECT VALUE, DESCRIPTION FROM CONFIGS WHERE KEY_NAME = %s"
        params = (key_name,)
        l_cursor.execute(query, params)
        return l_cursor.fetchall()[0]


def get_configs():
    with DatabaseManager().get_connection() as l_conn:
        l_cursor = l_conn.cursor()
        query = "SELECT KEY_NAME, VALUE, DESCRIPTION FROM CONFIGS"
        l_cursor.execute(query)
        return l_cursor.fetchall()


def get_config_value(key_name):
    with DatabaseManager().get_connection() as l_conn:
        l_cursor = l_conn.cursor()
        query = "SELECT VALUE FROM CONFIGS WHERE KEY_NAME = %s"
        params = (key_name,)
        l_cursor.execute(query, params)
        return l_cursor.fetchall()[0][0]


def delete_config(key_name):
    with DatabaseManager().get_connection() as l_conn:
        l_cursor = l_conn.cursor()
        query = "DELETE FROM CONFIGS WHERE KEY_NAME = %s"
        params = (key_name,)
        l_cursor.execute(query, params)
        l_conn.commit()


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Configs(client))
