from dotenv import load_dotenv
import os
import logging
import discord
from logging.handlers import TimedRotatingFileHandler

load_dotenv()

DISCORD_TOKEN = os.getenv("TOKEN")

DISCORD_GUILD = discord.Object(id=int(os.getenv("DOURADINHOS")))

LOG_FILE_PATH = "logs\logs.log"

ROLES = {'DOURADINHO_GOD': 759023632051339264,
         'DOURADINHO_MESTRE': 759023197004890152,
         'DOURADINHO': 760530815456378981,
         'DEV': 1171144045481959424,
         'Lorita': 760530316955090976
         }


# Configure the root logger
logging.basicConfig(level=logging.INFO,
                    filename=LOG_FILE_PATH,
                    datefmt='%Y-%m-%d %H:%M:%S',
                    format='%(asctime)s %(levelname)s %(name)s: %(message)s')

logger = logging.getLogger('discord-bot')

handler = TimedRotatingFileHandler(filename=LOG_FILE_PATH,
                                   when='h',
                                   interval=4,
                                   backupCount=6)
logger.addHandler(handler)


def get_logger():
    return logger
