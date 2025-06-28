import warnings

import discord
from discord import app_commands
from discord.ext import commands
from faceit import Faceit
from faceit.constants import GameID
from faceit.exceptions import APIError
import requests

import settings
from logic.utilities import create_dourabot_embed, country_code_to_flag, get_country_name

FACEIT_MAP_NAMES = {
    "de_inferno": "Inferno",
    "de_mirage": "Mirage",
    "de_nuke": "Nuke",
    "de_overpass": "Overpass",
    "de_vertigo": "Vertigo",
    "de_ancient": "Ancient",
    "de_anubis": "Anubis",
    "de_dust2": "Dust II",
    "cs_italy": "Italy",
    "cs_office": "Office",
    # Add more if needed
}

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
            return team
    return None


class FaceitCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger
        self.faceit = Faceit.data(f"{settings.FACEIT_API_KEY}")
        self.BASE_URL = "https://open.faceit.com/data/v4/"

    group = app_commands.Group(name="faceit", description="Faceit commands")

    def get_match_stats(self, match_id: str) -> dict:
        """
        Fetch match statistics for a given match ID.

        Args:
            match_id (str): The ID of the match.

        Returns:
            dict: The match statistics.
        """
        try:
            url = self.BASE_URL + f"matches/{match_id}/stats"
            headers = {
                "Authorization": f"Bearer {settings.FACEIT_API_KEY}",
                "Accept": "application/json"
            }
            response = requests.get(url, headers=headers).json()
            return response
        except APIError as e:
            self.logger.error(f"Faceit API Error: {e}")
            return {}

    def get_match_map(self, match_stats: dict) -> str:
        """
        Fetch the map name for a given match ID.

        Args:
            match_id (str): The ID of the match.

        Returns:
            str: The name of the map.
        """

        match_map = match_stats.get('rounds')[0].get('round_stats').get('Map')
        return FACEIT_MAP_NAMES.get(match_map) if match_map else "Unknown Map"

    def get_match_result(self, match_stats: dict, won: bool) -> str:
        """
        Fetch the map name for a given match ID.

        Args:
            match_id (str): The ID of the match.

        Returns:
            str: The name of the map.
        """

        score_str = match_stats.get('rounds')[0].get('round_stats').get('Score')

        left, right = score_str.split(" / ")
        left_score = int(left.strip())
        right_score = int(right.strip())

        if won:
            return f"{left_score} / {right_score}" if left_score > right_score else f"{right_score} / {left_score}"
        else:
            return f"{left_score} / {right_score}" if left_score < right_score else f"{right_score} / {left_score}"

    def get_match_kd(self, match_stats: dict, team_id: str, player_id: str) -> str:
        """
        Fetch the map name for a given match ID.

        Args:
            match_id (str): The ID of the match.

        Returns:
            str: The name of the map.
        """
        teams = match_stats.get('rounds')[0].get('teams')
        team = next((team for team in teams if team['team_id'] == team_id.__str__()), None)
        players = team.get('players')
        player = next((player for player in players if player['player_id'] == player_id.__str__()), None)
        player_stats = player.get('player_stats', {})
        return f"{player_stats.get('Kills', 0)} / {player_stats.get('Deaths', 0)}"

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
            await interaction.followup.send("Error fetching Faceit profile. Please check the username and try again.",
                                            ephemeral=True)

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

            embed = discord.Embed(title="🕹️ Last 5 Matches", color=0xFFA500)

            for match in history[:5]:
                winner = match.results.winner
                my_team, team_id = get_player_team(player.nickname, match.teams)
                won = winner == my_team
                result = "✅ Win" if won else "❌ Loss"
                faceit_url = match.faceit_url.__str__()

                match_stats = self.get_match_stats(match.id)
                match_map = self.get_match_map(match_stats)
                score = self.get_match_result(match_stats, won)
                kd = self.get_match_kd(match_stats, team_id.id, player.id)
                #is_mvp = max(team_kills) == player_kills

                time = f"<t:{match.started_at}:R>"

                field_title = f"🗺️ {match_map} - {time}"
                field_value = f"{result} | **Score:** {score} | **KD:** {kd}"  # Ideally replace with real score

                embed.add_field(name="", value=field_title, inline=True)
                embed.add_field(name="", value=field_value, inline=False)
                embed.add_field(name="", value=f"Match Link - [Click here]({faceit_url})", inline=False)
                embed.add_field(name="", value="" + "-" * 50, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)
        except APIError as e:
            self.logger.error(f"Faceit API Error: {e}")
            await interaction.followup.send("Error fetching match history. Please try again later.", ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(FaceitCog(client))
