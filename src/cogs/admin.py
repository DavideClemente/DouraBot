import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import ROLES


class admin(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    def is_role_allowed(self, *roles):
        def predicate(inter: discord.Interaction):
            return any(role in [r.id for r in inter.user.roles] for role in roles)
        return app_commands.check(predicate)

    @app_commands.command(name='show_logs', description='show recent bot logs')
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DOURADINHO_MESTRE'], ROLES['DEV'])
    async def show_logs(self, interaction: discord.Interaction, lines: int):
        '''Show the last n log lines'''
        multiline_string = "############## LOGS ##############".center(
            100) + "\n"

        with open(settings.LOG_FILE_PATH, "r") as file:
            lines_list = file.readlines()
            last_lines = lines_list[-lines:]
            multiline_string += "'''" + "\n".join(last_lines) + "'''"
        await interaction.response.send_message(multiline_string)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(admin(client))
