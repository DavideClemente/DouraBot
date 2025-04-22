import discord
from discord import app_commands
from discord.ext import commands

import settings


class SimRacing(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger

    @app_commands.command(name='calculate_fuel_time', description="Calculate the fuel needed for a race based on the total time")
    async def calculate_fuel_time(self, itr: discord.Interaction, total_time: int, lap_time: str, fuel_per_lap: float):
        """
        Calculate the fuel needed for a race based on the total time
        :param itr: Discord interaction
        :param total_time: Race length in minutes
        :param lap_time: Lap time in mm:ss
        :param fuel_per_lap: Fuel consumption per lap in liters
        :return: Recommended fuel in liters
        """

        minutes, seconds = map(int, lap_time.split(':'))
        lap_time_seconds = minutes * 60 + seconds

        total_time_seconds = total_time * 60
        laps = total_time_seconds / lap_time_seconds

        total_fuel = math.ceil(laps * fuel_per_lap)
        # Calculate recommended fuel by adding a 5% safety margin
        recommended_fuel = math.ceil(min_fuel * 1.05)

        await itr.response.send_message(f"Minimum fuel needed for the race: {total_fuel:.2f} liters ⛽.\nRecommended fuel: {recommended_fuel} liters ⚠️")

    @app_commands.command(name='calculate_fuel_laps',
                          description="Calculate the fuel needed for a race based on the total laps")
    async def calculate_fuel_laps(self, itr: discord.Interaction, laps: int, fuel_per_lap: float):
        """
        Calculate the fuel needed for a race based on the total laps
        :param itr: Discord interaction
        :param laps: Race laps
        :param fuel_per_lap: Fuel consumption per lap in liters
        :return: Recommended fuel in liters
        """

        total_fuel = math.ceil(laps * fuel_per_lap)
        # Calculate recommended fuel by adding a 5% safety margin
        recommended_fuel = math.ceil(min_fuel * 1.05)

        await itr.response.send_message(
            f"Minimum fuel needed for the race: {total_fuel:.2f} liters ⛽.\nRecommended fuel: {recommended_fuel} liters ⚠️")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(SimRacing(client))
