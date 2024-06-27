import dis
import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import DEV_CHANNEL, DOURADINHOS_AVATAR, GENERAL_CHANNEL, ROLES, DOURADINHOS_COLOR
from logic.utilities import is_role_allowed
import re


def remove_ansi_escape_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


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
        multiline_string = "############## LOGS ##############"
        lineList = ""
        with open(settings.LOG_FILE_PATH, "r") as file:
            lines_list = file.readlines()
            last_lines = lines_list[-lines:]
            lineList += '\n'.join(remove_ansi_escape_codes(last_lines))
        await interaction.followup.send(f'{multiline_string}\n>>> {lineList}')

    @show_logs.error
    async def show_logs_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            self.logger.info(
                f'User {interaction.user.display_name} tried calling show_logs')
            await interaction.response.send_message('Not allowed!', ephemeral=True)

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
        embed = discord.Embed(title=title, description=msg,
                              color=discord.Color.from_str(DOURADINHOS_COLOR))
        embed.set_author(name='DouraBot', icon_url=DOURADINHOS_AVATAR)
        if thumbnail is not None:
            embed.set_thumbnail(url=thumbnail)
        await channel.send(content="@everyone", embed=embed)
        await itr.response.send_message('Announcement made!')

    @announce.error
    async def announce_error(self, itr: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await itr.response.send_message(error, ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Admin(client))
