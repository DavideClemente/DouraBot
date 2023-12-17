from dotenv import load_dotenv
import os
import logging
import discord
from logging.handlers import TimedRotatingFileHandler

load_dotenv()

# CONSTANTS
ENVIRONMENT = os.getenv("ENVIRONMENT")
DISCORD_TOKEN = os.getenv(
    "TOKEN_DEV") if ENVIRONMENT == 'DEV' else os.getenv("TOKEN_PROD")
DISCORD_GUILD = discord.Object(id=int(os.getenv("DOURADINHOS")))

DOURADINHOS_IMAGE = 'https://www.nit.pt/wp-content/uploads/2016/10/ed3647fa-e8e1-47da-984f-4f166d66fa1c-754x394.jpg'

# CHANNEL IDS
GENERAL_CHANNEL = 756505500677308486
PRIVATE_DOURA_CHANNEL = 860682465185234944
DEV_CHANNEL = 1171143985595686983

# PATHS
LOG_FILE_PATH = os.path.join('.', 'logs', 'logs.log')
COGS_PATH = os.path.join('src', 'cogs')
DB_FILE_PATH = os.path.join('db', 'localdb.db')

ROLES = {'DOURADINHO_GOD': 759023632051339264,
         'DOURADINHO_MESTRE': 759023197004890152,
         'DOURADINHO': 760530815456378981,
         'DEV': 1171144045481959424,
         'Lorita': 760530316955090976
         }

IMDB_API = os.getenv("CLOUDFLARE_WORKER")

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
