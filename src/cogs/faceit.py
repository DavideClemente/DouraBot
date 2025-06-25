from lib2to3.pgen2.tokenize import group

import discord
import settings
from discord.ext import commands
from discord import app_commands


class Faceit(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger

    group = app_commands.Group(name="faceit", description="Faceit commands")

    @group.command(name="profile", description="Get Faceit profile information")
    async def profile(self, interaction: discord.Interaction, username: str) -> None:
        """Get Faceit profile information by username."""
        # Placeholder for actual Faceit API call
        await interaction.response.send_message(
            f"Profile information for {username} is not implemented yet.",
            ephemeral=True
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Faceit(client))
