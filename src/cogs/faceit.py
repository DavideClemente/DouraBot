import warnings

import discord
from discord import app_commands
from discord.ext import commands
from faceit import Faceit
from faceit.constants import GameID
from faceit.exceptions import APIError

import settings
from logic.utilities import create_dourabot_embed, country_code_to_flag, get_country_name

warnings.filterwarnings("ignore",
                        message="No model defined for this response. Validation and model parsing are unavailable.")


class FaceitCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger
        self.faceit = Faceit.data(f"{settings.FACEIT_API_KEY}")

    group = app_commands.Group(name="faceit", description="Faceit commands")

    @group.command(name="profile", description="Get Faceit profile information")
    async def profile(self, interaction: discord.Interaction, username: str) -> None:
        """Get Faceit profile information by username."""
        await interaction.response.defer()
        try:
            player = self.faceit.players.get(username)
            stats = self.faceit.players.stats(player.id, GameID.CS2)
            history = self.faceit.players.all_history(player.id, GameID.CS2)
            cs2_stats = stats.get('lifetime')
            cs2 = player.games.get(GameID.CS2)

            embed = create_dourabot_embed(title="Faceit Profile Info")

            embed.add_field(name="NickName",
                            value=player.nickname,
                            inline=True)
            embed.add_field(name="CS2 Name",
                            value=player.games[GameID.CS2].game_player_name,
                            inline=True)
            embed.add_field(name="🌍 Country",
                            value=f"{country_code_to_flag(player.country)} {get_country_name(player.country)}",
                            inline=True)
            embed.add_field(name="🏆 Level",
                            value=f"🔹 **{cs2.level}**",
                            inline=True)
            embed.add_field(name="📈 ELO",
                            value=cs2.elo,
                            inline=True)
            embed.add_field(name="🎯 Win Rate",
                            value=f"{cs2_stats.get('Win Rate %')}%",
                            inline=True)
            embed.add_field(name="🔫 K/D Ratio",
                            value=cs2_stats.get('Average K/D Ratio'),
                            inline=True)
            embed.add_field(name="🕹️ Games Played",
                            value=cs2_stats.get('Matches'),
                            inline=True)
            embed.add_field(name="📅 Last Match",
                            value=f"<t:{history[0].started_at}:R> (click [here]({history[0].faceit_url.__str__()}) for details)",
                            inline=False)

            embed.set_footer(text="Data powered by FACEIT API")

            await interaction.followup.send(embed=embed, ephemeral=True)
        except APIError as e:
            self.logger.error(f"Faceit API Error: {e}")
            await interaction.followup.send("Error fetching Faceit profile. Please check the username and try again.", ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(FaceitCog(client))
