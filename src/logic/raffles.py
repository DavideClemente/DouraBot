from itertools import permutations

import discord
from discord import Embed
from random import randint, shuffle
from settings import DOURADINHOS_IMAGE


def gifts_order(participants):
    shuffle(participants)
    lt = list()

    lt.append((participants[len(participants) - 1], participants[0]))
    for i in range(0, len(participants) - 1):
        a = participants[i]
        b = participants[i + 1]
        lt.append((a, b))
    return lt


def create_embed_gifts(title: str, description: str, footer: str, a: str, b: str):
    embed = discord.Embed(
        title=title.center(20),
        colour=discord.Colour.dark_teal(),
        description=description.center(30)
    )
    total_width = 30
    arrow_space = 5
    name_width = (total_width - arrow_space * 2) // 2

    embed.add_field(name=f'{str(a):<{name_width}}  {" " * arrow_space} ==> {" " * arrow_space} {str(b):<{name_width}}',
                    value="", inline=False)
    embed.set_author(name="DouraBot")
    embed.set_footer(text=footer)
    embed.set_thumbnail(
        url=DOURADINHOS_IMAGE)
    return embed
