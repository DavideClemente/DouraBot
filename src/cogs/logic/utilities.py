import discord
from discord import app_commands


def is_role_allowed(*roles):
    def predicate(inter: discord.Interaction):
        return any(role in [r.id for r in inter.user.roles] for role in roles)
    return app_commands.check(predicate)
