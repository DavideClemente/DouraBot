import discord
from discord import ui


class SecretSantaModal(ui.Modal):
    title = ui.TextInput(
        label="Title", style=discord.TextStyle.short, required=True)
    description = ui.TextInput(
        label="Description", style=discord.TextStyle.paragraph, required=True)
