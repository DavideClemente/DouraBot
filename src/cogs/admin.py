import dis
import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import DEV_CHANNEL, DOURADINHOS_AVATAR, GENERAL_CHANNEL, ROLES, DOURADINHOS_COLOR
from logic.utilities import is_role_allowed, create_dourabot_embed
import re


def remove_ansi_escape_codes(lines):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return '\n'.join(ansi_escape.sub('', line) for line in lines)


class Admin(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.get_logger()

    @app_commands.command(name='show_logs', description='show recent bot logs')
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DOURADINHO_MESTRE'], ROLES['DEV'])
    async def show_logs(self, interaction: discord.Interaction):
        """Shows the last lines of logs
        """
        lines = 10
        self.logger.info(
            f'User {interaction.user.display_name} called show_logs')
        await interaction.response.defer()
        message = "```"
        message += "############## LOGS ##############"
        lineList = ""
        with open(settings.LOG_FILE_PATH, "r") as file:
            lines_list = file.readlines()
            last_lines = lines_list[-lines:]
            lineList += remove_ansi_escape_codes(last_lines)
            message += "\n" + lineList
        message += "```"
        await interaction.followup.send(message, ephemeral=True)

    @show_logs.error
    async def show_logs_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            self.logger.info(
                f'User {interaction.user.display_name} tried calling show_logs')
            await interaction.response.send_message('Not allowed!', ephemeral=True)
        else:
            self.logger.error(
                f'Error in show_logs: {error}')
            await interaction.response.send_message('An error occurred!', ephemeral=True)

    @app_commands.command(name='announce', description='announce a message to the server')
    @app_commands.checks.cooldown(2, 5 * 60)
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DOURADINHO_MESTRE'])
    async def announce(self, itr: discord.Interaction, channel: discord.TextChannel, title: str, msg: str, thumbnail: str = None):
        """Announce a message to the server

        Args:
            :param thumbnail: Thumbnail url. Defaults to None.
            :param msg: Announcement description
            :param title: Announcement title
            :param itr: Discord interaction
            :param channel: Channel to send the announcement
        """
        self.logger.info(
            f'{itr.user.display_name} announced: Title - {title} | Message - {msg}')
        embed = create_dourabot_embed(
            title=title, description=msg.replace('\\n', '\n'))
        await channel.send(embed=embed)
        await itr.response.send_message('Announcement made!')

    @announce.error
    async def announce_error(self, itr: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await itr.response.send_message(error, ephemeral=True)

    @app_commands.command(name='load_cog', description='load a cog to enable its functionality')
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DEV'])
    async def load_cog(self, itr: discord.Interaction, cog_name: str):
        """Load a cog dynamically

        Args:
            itr (discord.Interaction): Discord interaction
            cog_name (str): Name of the cog to load (without .py extension)
        """
        await itr.response.defer()
        try:
            await self.client.load_extension(f'cogs.{cog_name}')
            self.logger.info(f'{itr.user.display_name} loaded cog: {cog_name}')
            await itr.followup.send(f'✅ Loaded cog: **{cog_name}**', ephemeral=True)
        except commands.ExtensionAlreadyLoaded:
            await itr.followup.send(f'⚠️ Cog **{cog_name}** is already loaded', ephemeral=True)
        except commands.ExtensionNotFound:
            await itr.followup.send(f'❌ Cog **{cog_name}** not found', ephemeral=True)
        except commands.ExtensionFailed as e:
            self.logger.error(f'Error loading cog {cog_name}: {e}')
            await itr.followup.send(f'❌ Error loading cog **{cog_name}**: {e}', ephemeral=True)

    @load_cog.error
    async def load_cog_error(self, itr: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            self.logger.info(
                f'User {itr.user.display_name} tried calling load_cog')
            await itr.response.send_message('Not allowed!', ephemeral=True)
        else:
            self.logger.error(f'Error in load_cog: {error}')
            await itr.response.send_message('An error occurred!', ephemeral=True)

    @app_commands.command(name='unload_cog', description='unload a cog to disable its functionality')
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DEV'])
    async def unload_cog(self, itr: discord.Interaction, cog_name: str):
        """Unload a cog dynamically

        Args:
            itr (discord.Interaction): Discord interaction
            cog_name (str): Name of the cog to unload (without .py extension)
        """
        await itr.response.defer()
        try:
            await self.client.unload_extension(f'cogs.{cog_name}')
            self.logger.info(
                f'{itr.user.display_name} unloaded cog: {cog_name}')
            await itr.followup.send(f'✅ Unloaded cog: **{cog_name}**', ephemeral=True)
        except commands.ExtensionNotLoaded:
            await itr.followup.send(f'⚠️ Cog **{cog_name}** is not currently loaded', ephemeral=True)
        except commands.ExtensionNotFound:
            await itr.followup.send(f'❌ Cog **{cog_name}** not found', ephemeral=True)
        except commands.ExtensionFailed as e:
            self.logger.error(f'Error unloading cog {cog_name}: {e}')
            await itr.followup.send(f'❌ Error unloading cog **{cog_name}**: {e}', ephemeral=True)

    @unload_cog.error
    async def unload_cog_error(self, itr: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            self.logger.info(
                f'User {itr.user.display_name} tried calling unload_cog')
            await itr.response.send_message('Not allowed!', ephemeral=True)
        else:
            self.logger.error(f'Error in unload_cog: {error}')
            await itr.response.send_message('An error occurred!', ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Admin(client))
