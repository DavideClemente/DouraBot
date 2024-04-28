import asyncio
import discord
import settings
from discord.ext import commands
from discord import app_commands, ChannelType
from settings import IMDB_API
from logic.utilities import rating_to_stars
import requests

logger = settings.get_logger()


class Movies(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = logger

    async def sendResults(self, thread: discord.Thread, imdb_data: dict):
        """Sends the results back to the server via a thread

        Args:
            thread (discord.Thread): Thread to send results to
            imdb_data (dict): Data from imdb
        """

        # If there is no image, the title is probably not valid
        if (imdb_data.get("image") is None):
            return

        movie_id = imdb_data["id"]
        details = requests.get(
            f'{IMDB_API}/title/{movie_id}').json()

        description = f'''
            Directors - {", ".join(details.get("directors", []))}
            Genres - {", ".join(details.get("genre", []))}
            Year - {details.get("year", "")}
            Rating - {rating_to_stars(details.get("rating", {}).get("star", 0))} (
                {details.get("rating", {}).get("star", 0)})
            Url - {imdb_data.get("imdb", "")}
        '''

        embed = discord.Embed(
            title=imdb_data.get('title', ''),
            description=description,
            url=imdb_data.get('imdb', ''),
            color=discord.Color.from_str(settings.DOURADINHOS_COLOR)
        )
        embed.set_image(url=imdb_data.get("image", ''))
        await thread.send(embed=embed)

    @app_commands.command(name='search_imdb', description='Search for a movie/series in imdb')
    async def search_imdb(self, itr: discord.Interaction,
                          title: str):
        """Search for a movie/series in imdb

        Args:
            itr (discord.Interaction): _description_
            title (str): Movie/Series title
        """
        self.logger.debug(
            f'User {itr.user.display_name} called search_imdb/{title}')
        await itr.response.defer()

        resp = requests.get(
            f'{IMDB_API}/search?query={title.strip().capitalize()}')

        if resp.status_code != 200:
            await itr.followup.send('Something went wrong!')
            return

        json_res = resp.json()

        await itr.followup.send("Sending results to a thread...")
        channel = self.client.get_channel(itr.channel_id)
        thread = await channel.create_thread(
            name=f'Search Imdb "{title}"',
            type=ChannelType.public_thread)

        for result in json_res["results"]:
            await self.sendResults(thread, result)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Movies(client))
