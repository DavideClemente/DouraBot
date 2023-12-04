from dotenv import load_dotenv
import os
import logging
import discord

load_dotenv()

DISCORD_TOKEN = os.getenv("TOKEN")

DISCORD_GUILD = discord.Object(id=int(os.getenv("DOURADINHOS")))

LOG_FILE_PATH = "../logs/infos.log"

logger = logging.getLogger(__name__)


console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('logs\infos.log')
console_handler.setLevel(logging.WARNING | logging.INFO)
file_handler.setLevel(logging.ERROR | logging.DEBUG)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


def get_logger():
    return logger


