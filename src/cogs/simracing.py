from math import ceil

import discord
import requests
from discord import app_commands
from discord.ext import commands, tasks
from logic.messages import get_latest_message_id_by_channel_id, delete_message_by_id, insert_message
from cogs.configs import get_config_value

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
        self.check_acc_status.start()

    def cog_unload(self) -> None:
        self.logger.info("SimRacing cog unloaded")

    @tasks.loop(minutes=6)
    async def check_acc_status(self):
        url: str = settings.ACC_STATUS_API
        channel_id: str = get_config_value('ACC_SERVER_STATUS')

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            status = data.get("status")
            color = discord.Color.green() if status == 1 else discord.Color.red()

            embed = discord.Embed(
                title="Assetto Corsa Competizione Server Status",
                timestamp=discord.utils.utcnow(),
                color=color
            )

            if status == 1:
                embed.add_field(name="Status", value="✅ Servers are UP!", inline=False)
                embed.add_field(name="Ping", value=f"{data.get('ping')} ms", inline=True)
                embed.add_field(name="Public Servers", value=f"{data.get('servers')}", inline=True)
                embed.add_field(name="Players Online", value=f"{data.get('players')}", inline=True)
            elif status == 0:
                embed.add_field(name="Status", value="❌ Servers are DOWN!", inline=False)
                embed.add_field(name="Down Since", value=f"{data.get('down_since')}", inline=False)
            else:
                embed.add_field(name="Status", value="⚠️ Unknown server status", inline=False)

            channel = self.client.get_channel(int(channel_id))
            if channel:
                last_message_id = get_latest_message_id_by_channel_id(channel_id)
                if last_message_id:
                    last_message = await channel.fetch_message(last_message_id)
                    if last_message:
                        await last_message.edit(embed=embed)
                        delete_message_by_id(last_message_id)
                        insert_message('acc_status', last_message_id, channel_id)
                        return
                else:
                    new_message = await channel.send(embed=embed, silent=True)
                    insert_message('acc_status', new_message.id, channel_id)
        except Exception as e:
            self.logger.error("Error checking ACC status:", e)

    @check_acc_status.before_loop
    async def before_check_acc_status(self):
        await self.client.wait_until_ready()

    @app_commands.command(name='calculate_fuel_time',
                          description="Calculate the fuel needed for a race based on the total time")
    async def calculate_fuel_time(self, itr: discord.Interaction, total_time: int, lap_time: str, fuel_per_lap: str):
        """
        Calculate the fuel needed for a race based on the total time
        :param itr: Discord interaction
        :param total_time: Race length in minutes
        :param lap_time: Lap time in mm:ss
        :param fuel_per_lap: Fuel consumption per lap in liters e.g. 2.5
        :return: Recommended fuel in liters
        """
        try:
            minutes, seconds = map(int, lap_time.split(':'))
            fuel_per_lap_float = convert_fuel(fuel_per_lap)
            lap_time_seconds = minutes * 60 + seconds

            total_time_seconds = total_time * 60
            laps = ceil(total_time_seconds / lap_time_seconds)

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
        :param fuel_per_lap: Fuel consumption per lap in liters e.g. 2.5
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
