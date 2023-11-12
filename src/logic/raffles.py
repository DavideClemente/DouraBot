from itertools import permutations

import discord
from discord import Embed
from random import randint


def gifts_order(participants):
    perms = list(permutations(participants))
    index = randint(0, len(perms) - 1)

    gift_order = list(perms[index])
    lt = list()

    lt.append((gift_order[len(gift_order) - 1], gift_order[0]))
    for i in range(0, len(participants) - 1):
        a = gift_order[i]
        b = gift_order[i + 1]
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
        url='https://www.nit.pt/wp-content/uploads/2016/10/ed3647fa-e8e1-47da-984f-4f166d66fa1c-754x394.jpg')
    return embed
