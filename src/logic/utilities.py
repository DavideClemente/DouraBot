import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime


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


def convert_to_datetime(date_str: str) -> datetime:
    try:
        # Attempt to parse the argument as a date
        date_obj = datetime.strptime(date_str, '%m-%d')
        return date_obj
    except ValueError:
        # If parsing fails, raise an exception or handle the error accordingly
        raise ValueError("Invalid date format. Please use MM-DD.")


def get_persistent_message(db, event):
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT ID FROM PERSISTENT_MESSAGES WHERE EVENT = %s", (event,))
        return cursor.fetchone()


def insert_persistent_message(db, event):
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO PERSISTENT_MESSAGES (EVENT) VALUES(%s)", (event,))
        db.commit()


def hex_to_rgba(hex_color: str):
    hex_color = hex_color.lstrip('0x#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (255,)
