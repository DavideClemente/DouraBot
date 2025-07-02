import discord
import requests
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Select, View

import settings
from logic.utilities import is_role_allowed
from settings import ROLES

currencies = [('GBP', '🇬🇧'), ('USD', '🇺🇸'), ('EUR', '🇪🇺'),
              ('JPY', '🇯🇵'), ('CHF', '🇨🇭'), ('AUD', '🇦🇺'), ('CAD', '🇨🇦'), ('INR', '🇮🇳'), ('BRL', '🇧🇷')]


class MySelectView(View):
    def __init__(self, amount):
        self.fromCurrency = None
        self.toCurrency = None
        self.amount = amount

        super().__init__()

    @discord.ui.select(
        cls=Select,
        placeholder="Select currency to convert from",
        options=[discord.SelectOption(
            label=currency[0], value=currency[0], emoji=currency[1])
            for currency in currencies],
        row=1)
    async def select_callback(self, interaction: discord.Interaction, select: Select):
        self.fromCurrency = select.values[0]
        return await interaction.response.defer()

    @discord.ui.select(
        cls=Select,
        placeholder="Select currency to convert to",
        options=[discord.SelectOption(
            label=currency[0], value=currency[0], emoji=currency[1])
            for currency in currencies],
        row=2)
    async def select_callback2(self, interaction: discord.Interaction, select: Select):
        self.toCurrency = select.values[0]
        return await interaction.response.defer()

    @discord.ui.button(
        label="Convert",
        row=3,
        style=discord.ButtonStyle.primary,
    )
    async def convert(self, interaction: discord.Interaction, button: Button):
        if self.fromCurrency is None or self.toCurrency is None:
            return await interaction.response.send_message("Please select both currencies", ephemeral=True)

        api_response_json = requests.get(
            f'{settings.CURRENCY_API}&currencies={self.toCurrency}&base_currency={self.fromCurrency}').json()

        if api_response_json['data'] is not None:
            data = api_response_json['data']
            return await interaction.response.edit_message(view=None, content=f'🪙 Result: {self.amount} {self.fromCurrency} = {round(self.amount * float(data[self.toCurrency]), 2)} {self.toCurrency} 🪙')
        else:
            return await interaction.response.edit_message('Error while performing conversion', ephemeral=True)


class Currency(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.get_logger()

    @ app_commands.command(name='convert_currency', description="Convert any amount from one currency to another")
    async def convert_currency(self, itr: discord.Interaction, amount: float):
        """Convert any amount from one currency to another

        Args:
            itr (discord.Interaction): _description_
            amount (float): Amount to be converted
        """

        view = MySelectView(amount=amount)

        await itr.response.send_message("Select currency to convert to", view=view, ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Currency(client))
