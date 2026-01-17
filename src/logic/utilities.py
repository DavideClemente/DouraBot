from dis import disco
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from py_linq.py_linq import Enumerable
import pycountry
import settings



def bold_msg(msg: str) -> str:
    """
    Returns the message wrapped in double asterisks for bold formatting.
    """
    return f"**{msg}**"


def is_role_allowed(*roles):
    def predicate(inter: discord.Interaction) -> bool:
        user_role_ids = Enumerable(inter.user.roles).select(lambda r: r.id).to_list()
        return Enumerable(roles).any(lambda role: role in user_role_ids)

    return app_commands.check(predicate)


def rating_to_stars(rating: float) -> str:
    full_stars = int(rating / 2)
    half_star = int((rating % 2) != 0)

    return "⭐" * full_stars + ("½" if half_star else "")


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
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def create_dourabot_embed(title: str, 
                          description: str = "", 
                          color: str = settings.DOURADINHOS_COLOR,
                          thumbnail_url: str = settings.DOURADINHOS_IMAGE) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=discord.Color.from_str(color))
    embed.set_author(name="DouraBot", icon_url=settings.DOURADINHOS_AVATAR)
    embed.set_thumbnail(url=thumbnail_url)
    return embed


def country_code_to_flag(country_code: str) -> str:
    """
    Converts a 2-letter country code (e.g., 'US', 'PT') to the corresponding emoji flag.
    """
    return ''.join(
        chr(127397 + ord(char))
        for char in country_code.upper()
    )


def get_country_name(country_code: str) -> str:
    try:
        return pycountry.countries.get(alpha_2=country_code.upper()).name
    except AttributeError:
        return country_code  # fallback if code is invalid or unknown
