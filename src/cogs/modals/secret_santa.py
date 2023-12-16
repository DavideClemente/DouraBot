from typing import Optional
import discord
from discord import ui
from discord.interactions import Interaction
from discord.utils import MISSING


class SecretSantaModal(ui.Modal):
    def __init__(self, itr: discord.Interaction) -> None:
        self.itr = itr
        self.title = ui.TextInput(
            label="Title", style=discord.TextStyle.short, required=True)
        self.add_item(self.title)
        self.description = ui.TextInput(
            label="Description", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.followup.send(f'Title = {self.title} | Description = {self.description}')
