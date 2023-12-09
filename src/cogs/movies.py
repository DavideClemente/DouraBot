import discord
import settings
from discord.ext import commands
from discord import app_commands, ChannelType
from settings import ROLES, IMDB_API
from .logic.utilities import rating_to_stars, is_role_allowed
import sys
import requests
import json
import random

logger = settings.get_logger()


class Movies(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = logger

    async def sendResults(self, thread: discord.Thread, result):
        # result = json_res["results"][0]
        movie_id = result["id"]
        details = requests.get(
            f'{IMDB_API}/title/{movie_id}').json()

        description = f'''
                Directors - {", ".join(details["directors"])}
                Genres - {", ".join(details["genre"])}
                Year - {details["year"]}
                Rating - {rating_to_stars(details["rating"]["star"])} ({details["rating"]["star"]})
                Url - {result["imdb"]}
            '''

        embed = discord.Embed(
            title=result['title'],
            description=description,
            url=result['imdb']
        )
        embed.set_image(url=result["image"])
        await thread.send(embed=embed)

    @app_commands.command(name='search_imdb', description='Search for a movie/series in imdb')
    async def search_imdb(self, itr: discord.Interaction,
                          title: str):
        ''''Search for a movie/series in imdb'''
        self.logger.info(
            f'User {itr.user.display_name} called show_logs')
        await itr.response.defer()

        resp = requests.get(
            f'{IMDB_API}/search?query={title.strip().capitalize()}')

        if resp.status_code != 200:
            await itr.followup.send('Something went wrong!')
            return

        json_res = resp.json()

        channel = self.client.get_channel(itr.channel_id)
        thread = await channel.create_thread(
            name=f'Search Imdb "{title}"',
            type=ChannelType.public_thread)
        await itr.followup.send(json_res["message"])
       # await thread.send()

        for result in json_res["results"]:
            await self.sendResults(thread, result)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Movies(client))
