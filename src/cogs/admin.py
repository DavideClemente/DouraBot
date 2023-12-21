import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import ROLES
from logic.utilities import is_role_allowed


class admin(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.get_logger()

    @app_commands.command(name='show_logs', description='show recent bot logs')
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DOURADINHO_MESTRE'], ROLES['DEV'])
    async def show_logs(self, interaction: discord.Interaction, lines: int):
        """Shows the last lines of logs

        Args:
            interaction (discord.Interaction): _description_
            lines (int): Number of lines you want to retrieve
        """
        self.logger.info(
            f'User {interaction.user.display_name} called show_logs')
        await interaction.response.defer()
        multiline_string = "############## LOGS ##############"
        lineList = ""
        with open(settings.LOG_FILE_PATH, "r") as file:
            lines_list = file.readlines()
            last_lines = lines_list[-lines:]
            lineList += '\n'.join(last_lines)
        await interaction.followup.send(f'{multiline_string}\n>>> {lineList}')

    @show_logs.error
    async def show_logs_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            self.logger.info(
                f'User {interaction.user.display_name} tried calling show_logs')
            await interaction.response.send_message('Not allowed!', ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(admin(client))
