import discord
from discord import app_commands


def is_role_allowed(*roles):
    def predicate(inter: discord.Interaction):
        return any(role in [r.id for r in inter.user.roles] for role in roles)
    return app_commands.check(predicate)


def rating_to_stars(rating: float):
    full_stars = int(rating / 2)
    half_star = int((rating % 2) != 0)

    return "⭐" * full_stars + ("½" if half_star else "")

def ifNoneThenString(value):
    return value if value is not None else ""