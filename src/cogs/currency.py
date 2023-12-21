import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import ROLES
from logic.utilities import is_role_allowed
import requests
import json


class Currency(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.get_logger()
        self.currencies = ['GBP', 'USD', 'EUR',
                           'JPY', 'CHF', 'AUD', 'CAD', 'INR', 'BZR']

    @app_commands.command(name='convert_currency', description="Convert any amount from one currency to another")
    async def convert_currency(self, itr: discord.Interaction, currency1: str, currency2: str, amount: float):
        """Convert any amount from one currency to another

        Args:
            itr (discord.Interaction): _description_
            currency1 (str): Currency to convert from
            currency2 (str): Currency to convert to
            amount (float): Amount to be converted
        """
        if currency1 not in self.currencies:
            await itr.response.send_message(f'{currency1} is not supported!', ephemeral=True)

        if currency2 not in self.currencies:
            await itr.response.send_message(f'{currency2} is not supported!', ephemeral=True)

        api_response_json = requests.get(
            f'{settings.CURRENCY_API}&currencies={currency2}&base_currency={currency1}').json()

        if (api_response_json['data'] is not None):
            data = api_response_json['data']
            await itr.response.send_message(f'Result: {amount} {currency1} => {round(amount * float(data[currency2]), 2)} {currency2}')
        else:
            await itr.response.send_message('Error while performing conversion', ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Currency(client))
