import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import ROLES
import sys
import requests
import json
import random

logger = settings.get_logger()


class Movies(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = logger

    @app_commands.command(name='search_imdb', description='Search for a movie/series in imdb')
    async def search_imdb(self, itr: discord.Interaction,
                          title: str):
        ''''Search for a movie/series in imdb'''
        self.logger.info(
            f'User {itr.user.display_name} called show_logs')
        await itr.response.defer()
        response = {
            "query": "Joker",
            "message": "Found 7 titles",
            "results": [
                {
                    "id": "tt7286456",
                    "title": "Joker",
                    "year": 2019,
                    "type": "movie",
                    "image": "https://m.media-amazon.com/images/M/MV5BNGVjNWI4ZGUtNzE0MS00YTJmLWE0ZDctN2ZiYTk2YmI3NTYyXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_UY396_CR6,0,267,396_AL_.jpg",
                    "image_large": "https://m.media-amazon.com/images/M/MV5BNGVjNWI4ZGUtNzE0MS00YTJmLWE0ZDctN2ZiYTk2YmI3NTYyXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                    "api_path": "/title/tt7286456",
                    "imdb": "https://www.imdb.com/title/tt7286456"
                },
                {
                    "id": "tt11315808",
                    "title": "Joker: Folie à Deux",
                    "year": 2024,
                    "type": "movie",
                    "image": "https://m.media-amazon.com/images/M/MV5BODUyODM1OGEtNTY3ZC00OTFjLTkyNDgtODU4MTk5NzkzYmQ5XkEyXkFqcGdeQXVyNjczMjc4NTA@._V1_UY396_CR6,0,258,396_AL_.jpg",
                    "image_large": "https://m.media-amazon.com/images/M/MV5BODUyODM1OGEtNTY3ZC00OTFjLTkyNDgtODU4MTk5NzkzYmQ5XkEyXkFqcGdeQXVyNjczMjc4NTA@._V1_.jpg",
                    "api_path": "/title/tt11315808",
                    "imdb": "https://www.imdb.com/title/tt11315808"
                },
                {
                    "id": "tt5611648",
                    "title": "Joker",
                    "year": 2016,
                    "type": "movie",
                    "image": "https://m.media-amazon.com/images/M/MV5BMTg3NzU5Mzg1MF5BMl5BanBnXkFtZTgwODIxMDg4MDI@._V1_UY396_CR6,0,289,396_AL_.jpg",
                    "image_large": "https://m.media-amazon.com/images/M/MV5BMTg3NzU5Mzg1MF5BMl5BanBnXkFtZTgwODIxMDg4MDI@._V1_.jpg",
                    "api_path": "/title/tt5611648",
                    "imdb": "https://www.imdb.com/title/tt5611648"
                },
                {
                    "id": "tt2548208",
                    "title": "Poker Night",
                    "year": 2014,
                    "type": "movie",
                    "image": "https://m.media-amazon.com/images/M/MV5BOTc5NjIyODM2M15BMl5BanBnXkFtZTgwMTMyNzE4MDE@._V1_UY396_CR6,0,267,396_AL_.jpg",
                    "image_large": "https://m.media-amazon.com/images/M/MV5BOTc5NjIyODM2M15BMl5BanBnXkFtZTgwMTMyNzE4MDE@._V1_.jpg",
                    "api_path": "/title/tt2548208",
                    "imdb": "https://www.imdb.com/title/tt2548208"
                },
                {
                    "id": "tt1918886",
                    "title": "Joker",
                    "year": 2012,
                    "type": "movie",
                    "image": "https://m.media-amazon.com/images/M/MV5BMjE0NjIxODMxN15BMl5BanBnXkFtZTcwMjM5MDcxOA@@._V1_UY396_CR6,0,296,396_AL_.jpg",
                    "image_large": "https://m.media-amazon.com/images/M/MV5BMjE0NjIxODMxN15BMl5BanBnXkFtZTcwMjM5MDcxOA@@._V1_.jpg",
                    "api_path": "/title/tt1918886",
                    "imdb": "https://www.imdb.com/title/tt1918886"
                },
                {
                    "id": "tt13212978",
                    "title": "Joker: Part II",
                    "year": 2021,
                    "type": "movie",
                    "image": "https://m.media-amazon.com/images/M/MV5BNzY5YWY3N2QtNDVlYi00NmE5LTgyOGItMDE0YTQzMWM2NzVjXkEyXkFqcGdeQXVyNTUzNDMzOTY@._V1_UY396_CR6,0,297,396_AL_.jpg",
                    "image_large": "https://m.media-amazon.com/images/M/MV5BNzY5YWY3N2QtNDVlYi00NmE5LTgyOGItMDE0YTQzMWM2NzVjXkEyXkFqcGdeQXVyNTUzNDMzOTY@._V1_.jpg",
                    "api_path": "/title/tt13212978",
                    "imdb": "https://www.imdb.com/title/tt13212978"
                },
                {
                    "id": "tt0102166",
                    "title": "Joker",
                    "year": 1991,
                    "type": "movie",
                    "image": "https://m.media-amazon.com/images/M/MV5BMDUzMjNjZWUtMjY5Ny00YjQ0LWEwYjgtMWYzOWU1MDdkOThhXkEyXkFqcGdeQXVyMjUyNDk2ODc@._V1_UY396_CR6,0,276,396_AL_.jpg",
                    "image_large": "https://m.media-amazon.com/images/M/MV5BMDUzMjNjZWUtMjY5Ny00YjQ0LWEwYjgtMWYzOWU1MDdkOThhXkEyXkFqcGdeQXVyMjUyNDk2ODc@._V1_.jpg",
                    "api_path": "/title/tt0102166",
                    "imdb": "https://www.imdb.com/title/tt0102166"
                }
            ]
        }
        result = response["results"][random.randint(
            0, len(response["results"]) - 1)]
        embed = discord.Embed(
            title=result['title'],
            description=f'{result["title"]} - {result["year"]}',
            url=result['imdb']
        )
        embed.set_image(url=result["image"])
        await itr.followup.send(embed=embed)
        # url = 'https://imdb-api.projects.thetuhin.com/search?query=Joker'
        # headers = {
        #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        # response = requests.get(url=url, headers=headers)
        # if response.status_code == 200:
        #     data = response.json()
        #     await itr.followup.send(json.dumps(data))
        # else:
        #     await itr.followup.send('Unsuccessfull')


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Movies(client))
