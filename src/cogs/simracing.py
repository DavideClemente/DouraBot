import discord
from discord import app_commands
from discord.ext import commands
import math

import settings


def convert_fuel(fuel_str: str):
    """Convert fuel string to float"""
    try:
        return float(fuel_str)
    except ValueError:
        raise InvalidFuelException("Invalid fuel format. Please use a valid number.")


class SimRacing(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger

    @app_commands.command(name='calculate_fuel_time',
                          description="Calculate the fuel needed for a race based on the total time")
    async def calculate_fuel_time(self, itr: discord.Interaction, total_time: int, lap_time: str, fuel_per_lap: str):
        """
        Calculate the fuel needed for a race based on the total time
        :param itr: Discord interaction
        :param total_time: Race length in minutes
        :param lap_time: Lap time in mm:ss
        :param fuel_per_lap: Fuel consumption per lap in liters e.g. 2,5
        :return: Recommended fuel in liters
        """
        try:
            minutes, seconds = map(int, lap_time.split(':'))
            fuel_per_lap_float = convert_fuel(fuel_per_lap)
            lap_time_seconds = minutes * 60 + seconds

            total_time_seconds = total_time * 60
            laps = math.ceil(total_time_seconds / lap_time_seconds)

            total_fuel = laps * fuel_per_lap_float
            recommended_fuel = ceil(total_fuel + (fuel_per_lap_float * 1.5))

            response = []
            response.append(f"⛽ Minimum fuel needed for the race: {round(total_fuel, 1):.1f} liters ⛽.")
            response.append(f"⚠️ Recommended fuel: {round(recommended_fuel, 1):.1f} liters ⚠️")
            response.append(f"Total laps: {laps}.")

            await itr.response.send_message(
                "\n".join(response),
                ephemeral=True)
        except ValueError:
            await itr.response.send_message("Invalid lap time format. Please use mm:ss.", ephemeral=True)
        except ZeroDivisionError:
            await itr.response.send_message("Lap time cannot be zero.", ephemeral=True)
        except InvalidFuelException:
            await itr.response.send_message("Invalid fuel format. Please use a valid number. e.g. 1.2", ephemeral=True)
        except Exception as e:
            await itr.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name='calculate_fuel_laps',
                          description="Calculate the fuel needed for a race based on the total laps")
    async def calculate_fuel_laps(self, itr: discord.Interaction, laps: int, fuel_per_lap: str):
        """
        Calculate the fuel needed for a race based on the total laps
        :param itr: Discord interaction
        :param laps: Race laps
        :param fuel_per_lap: Fuel consumption per lap in liters e.g. 2,5
        :return: Recommended fuel in liters
        """

        try:
            fuel_per_lap_float = convert_fuel(fuel_per_lap)
            total_fuel = laps * fuel_per_lap_float
            recommended_fuel = ceil(total_fuel + (fuel_per_lap_float * 1.5))

            await itr.response.send_message(
                f"⛽ Minimum fuel needed for the race: {total_fuel:.1f} liters ⛽.\n⚠️ Recommended fuel: {recommended_fuel} liters ⚠️",
                ephemeral=True)
        except ValueError | TypeError:
            await itr.response.send_message("Invalid values. Please use valid values.", ephemeral=True)
        except InvalidFuelException:
            await itr.response.send_message("Invalid fuel format. Please use a valid number. e.g. 1.2", ephemeral=True)
        except Exception as e:
            await itr.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)


class InvalidFuelException(Exception):
    pass


async def setup(client: commands.Bot) -> None:
    await client.add_cog(SimRacing(client))
