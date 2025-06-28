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


def get_player_team(player_nickname: str, teams: list) -> dict:
    """
    Determine which team the player belongs to based on their ID.

    Args:
        player_id (str): The ID of the player.
        teams (list): A list of team objects, each containing player IDs.

    Returns:
        dict: The team object the player belongs to, or None if not found.
    """
    for team in teams:
        if player_nickname in [player.nickname for player in team[1].players]:
            return team[0]
    return None


class FaceitCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger
        self.faceit = Faceit.data(f"{settings.FACEIT_API_KEY}")

    group = app_commands.Group(name="faceit", description="Faceit commands")

    @group.command(name="profile", description="Get FACEIT profile information")
    async def profile(self, interaction: discord.Interaction, username: str) -> None:
        """Get Faceit profile information by username."""
        await interaction.response.defer()
        try:
            player = self.faceit.players.get(username)
            stats = self.faceit.players.stats(player.id, GameID.CS2)
            history = self.faceit.players.all_history(player.id, GameID.CS2)
            cs2_stats = stats.get('lifetime')
            cs2 = player.games.get(GameID.CS2)

            embed = create_dourabot_embed(title="FACEIT Profile Info")

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

    @group.command(name="match_history", description="Get FACEIT player match history")
    async def match_history(self, interaction: discord.Interaction, username: str) -> None:
        """Fetch and display match history for a given player."""
        await interaction.response.defer()
        try:
            player = self.faceit.players.get(username)
            history = self.faceit.players.all_history(player.id, GameID.CS2)
            if not history:
                await interaction.followup.send("No match history found for this player.", ephemeral=True)
                return

            embed = create_dourabot_embed(title=f"🕹️ Last 5 Matches - {player.nickname}")

            for match in history[:5]:
                winner = match.results.winner
                match_1 = self.faceit.matches.get(match.id)
                my_team = get_player_team(player.nickname, match.teams)
                result = "Win" if winner == my_team else "Loss"
                embed.add_field(
                    name=f":arrow_right_hook: Match ID: {match.id}",
                    value=f"Date: <t:{match.started_at}:R> | Result: {result} | [Details]({match.faceit_url})",
                    inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)
        except APIError as e:
            self.logger.error(f"Faceit API Error: {e}")
            await interaction.followup.send("Error fetching match history. Please try again later.", ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(FaceitCog(client))
