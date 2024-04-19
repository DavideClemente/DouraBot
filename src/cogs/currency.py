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

        drp_from = discord.ui.Select(
            placeholder="Select currency to convert from",
            options=[discord.SelectOption(label=currency)
                     for currency in self.currencies]
        )

        drp_to = discord.ui.Select(
            placeholder="Select currency to convert to",
            options=[discord.SelectOption(label=currency)
                     for currency in self.currencies]
        )

        btn = discord.ui.Button(
            label="Convert", style=discord.ButtonStyle.primary)

        view = discord.ui.View().add_item(drp_from).add_item(drp_to).add_item(btn)

        await itr.response.send_message("Select currencies to convert", view=view)

        from_resp = await self.client.wait_for('select_option', check=lambda m: m.user.id == itr.user.id)
        to_resp = await self.client.wait_for('select_option', check=lambda m: m.user.id == itr.user.id)

        # currency1 = currency1.upper()
        # currency2 = currency2.upper()
        # if currency1 not in self.currencies:
        #     await itr.response.send_message(f'{currency1} is not supported!', ephemeral=True)

        # if currency2 not in self.currencies:
        #     await itr.response.send_message(f'{currency2} is not supported!', ephemeral=True)

        api_response_json = requests.get(
            f'{settings.CURRENCY_API}&currencies={to_resp.values[0]}&base_currency={from_resp.values[0]}').json()

        if (api_response_json['data'] is not None):
            data = api_response_json['data']
            await itr.response.send_message(f'🪙 Result: {amount} {currency1} => {round(amount * float(data[currency2]), 2)} {currency2} 🪙')
        else:
            await itr.response.send_message('Error while performing conversion', ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Currency(client))
