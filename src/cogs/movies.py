import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import ROLES
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
                }
            ]
        }

        details = {
            "id": "tt7286456",
            "review_api_path": "/reviews/tt7286456",
            "imdb": "https://www.imdb.com/title/tt7286456",
            "contentType": "movie",
            "contentRating": "R",
            "isSeries": False,
            "productionStatus": "released",
            "isReleased": True,
            "title": "Joker",
            "image": "https://m.media-amazon.com/images/M/MV5BNGVjNWI4ZGUtNzE0MS00YTJmLWE0ZDctN2ZiYTk2YmI3NTYyXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
            "images": [
                "https://m.media-amazon.com/images/M/MV5BY2MzMmRiZDQtMmQyMy00ODM3LTk1ZTYtNzYzYjliZTExY2YwXkEyXkFqcGdeQXVyNTM3MDMyMDQ@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BNDM2ZWYzZWItYTdiMS00ZGUzLWFkZTMtYWE3YzRkNGJmZDk1XkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BMDNkYTMzZjctYjg5YS00MDgwLTg2MGYtMWNmOWY3Nzg0ZDVlXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BMjk4Nzg5NjktMGMxMS00NjhjLThmNjItM2JjM2VjYjAwMjcyXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BYmZlOTY2OGUtYWY2Yy00NGE0LTg5YmQtNmM2MmYxOWI2YmJiXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BNmUzNDgwYjAtM2IyYS00ZTc3LWJjMDgtZTQ2MzA5N2IyMDZhXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BZDgzMzEzNDMtZThlNC00OTc3LWFlOGQtNGQ2ODFmYmNhOTA4XkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BODJmZTI4MmMtMTc5Mi00OTZlLWFiNDItMTNlZjQyMzUxMmQyXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BMjI0Nzk4ODctYWNlOC00Njg5LThiNTMtZDNjOTllODNlNWZlXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BOWM3ZDI1ZDAtYTZlZS00M2MzLWJhNTQtOWQxNmM5YmMzYjdiXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BZDJkOWFiM2QtYWExNS00YjQ3LTkyYTktMjllODBlY2UzMjQ2XkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BZGUzMWI4ZDktNTEzYi00ZmNiLThhNzItZDkwZDk2NTg5ZGNiXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg",
                "https://m.media-amazon.com/images/M/MV5BYWQ4Mjk0Y2QtMDg0Mi00NWVjLWE2YmQtZmJjNGNmZThmMDQxXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_.jpg"
            ],
            "plot": "During the 1980s, a failed stand-up comedian is driven insane and turns to a life of crime and chaos in Gotham City while becoming an infamous psychopathic crime figure.",
            "runtime": "2h 2m",
            "runtimeSeconds": 7320,
            "rating": {
                "count": 1427201,
                "star": 8.4
            },
            "award": {
                "wins": 121,
                "nominations": 239
            },
            "genre": [
                "Crime",
                "Drama",
                "Thriller"
            ],
            "releaseDetailed": {
                "date": "2019-10-04T00:00:00.000Z",
                "day": 4,
                "month": 10,
                "year": 2019,
                "releaseLocation": {
                    "country": "United States",
                    "cca2": "US"
                },
                "originLocations": [
                    {
                        "country": "United States",
                        "cca2": "US"
                    },
                    {
                        "country": "Canada",
                        "cca2": "CA"
                    }
                ]
            },
            "year": 2019,
            "spokenLanguages": [
                {
                    "language": "English",
                    "id": "en"
                },
                {
                    "language": "German",
                    "id": "de"
                }
            ],
            "filmingLocations": [
                "1150 Anderson Ave, The Bronx, New York City, New York, USA"
            ],
            "actors": [
                "Joaquin Phoenix",
                "Robert De Niro",
                "Zazie Beetz"
            ],
            "actors_v2": [
                {
                    "id": "nm0001618",
                    "name": "Joaquin Phoenix"
                },
                {
                    "id": "nm0000134",
                    "name": "Robert De Niro"
                },
                {
                    "id": "nm5939164",
                    "name": "Zazie Beetz"
                }
            ],
            "creators": [

            ],
            "creators_v2": [

            ],
            "directors": [
                "Todd Phillips"
            ],
            "directors_v2": [
                {
                    "id": "nm0680846",
                    "name": "Todd Phillips"
                }
            ],
            "writers": [
                "Todd Phillips",
                "Scott Silver",
                "Bob Kane"
            ],
            "writers_v2": [
                {
                    "id": "nm0680846",
                    "name": "Todd Phillips"
                },
                {
                    "id": "nm0798788",
                    "name": "Scott Silver"
                },
                {
                    "id": "nm0004170",
                    "name": "Bob Kane"
                }
            ],
            "top_credits": [
                {
                    "id": "director",
                    "name": "Director",
                    "credits": [
                        "Todd Phillips"
                    ]
                },
                {
                    "id": "writer",
                    "name": "Writers",
                    "credits": [
                        "Todd Phillips",
                        "Scott Silver",
                        "Bob Kane"
                    ]
                },
                {
                    "id": "cast",
                    "name": "Stars",
                    "credits": [
                        "Joaquin Phoenix",
                        "Robert De Niro",
                        "Zazie Beetz"
                    ]
                }
            ]
        }
        result = response["results"][random.randint(
            0, len(response["results"]) - 1)]

        description = f'''
            Directors - {", ".join(details["directors"])}
            Genres - {", ".join(details["genre"])}
            Year - {details["year"]}
            Rating - {rating_to_stars(details["rating"]["star"])} ({details["rating"]["star"]})
        '''

        embed = discord.Embed(
            title=result['title'],
            description=description,
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
