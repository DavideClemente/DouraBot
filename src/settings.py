from dotenv import load_dotenv
import os
import logging
import discord
from logging.handlers import TimedRotatingFileHandler

load_dotenv()

# ENVIRONMENT
ENVIRONMENT = os.getenv("ENVIRONMENT", "PROD")
IS_DEV = True if ENVIRONMENT == 'DEV' else False
if IS_DEV:
    DB_HOST = 'localhost'
    DB_USER = 'dourabot'
    DB_PASSWORD = 'dourabot123'
    DB_DATABASE = 'master'
else:
    DB_HOST = 'mariadoura'
    DB_USER = 'root'
    DB_PASSWORD = 'davide123'
    DB_DATABASE = 'master'
DB_PORT = 3306

# CONSTANTS
DISCORD_TOKEN = os.getenv(
    "TOKEN_DEV") if IS_DEV else os.getenv("TOKEN_PROD")
DISCORD_ID = int(os.getenv("DOURADINHOS"))
DISCORD_GUILD = discord.Object(id=int(os.getenv("DOURADINHOS")))
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
FACEIT_API_KEY = os.getenv("FACEIT_API_KEY")

DOURADINHOS_COLOR = '0x#f28e0e'
DOURADINHOS_IMAGE = 'https://www.nit.pt/wp-content/uploads/2016/10/ed3647fa-e8e1-47da-984f-4f166d66fa1c-754x394.jpg'
DOURADINHOS_AVATAR = 'https://cdn.discordapp.com/avatars/1171141490806898809/481485d7a8de607ddcf5a921872f518a.png'

# CHANNEL IDS
WELCOME_CHANNEL = 856155750975143936
MODS_CHANNEL = 1233748279376875531
GENERAL_CHANNEL = 756505500677308486
PRIVATE_DOURA_CHANNEL = 860682465185234944
DEV_CHANNEL = 1171143985595686983
ROLES_CHANNEL = 1236703744524025947


# ASSETO CORSA LINKS
CARS_LINK = 'https://drive.google.com/drive/folders/1FaIDOQ2L2jpUzsatK1CmBlR77BqyhUIJ?usp=drive_link'
TRACKS_LINK = 'https://drive.google.com/drive/folders/1DUxemFJuFimWt3OqGI-3pCdq99Vv0L2i?usp=drive_link'
APPS_LINK = 'https://drive.google.com/drive/folders/18rLa9etKzhzrpVfz4rzYCJ5h7tEDwNbC?usp=drive_link'

# ACC LINKS
ACC_STATUS_API = 'https://acc-status.jonatan.net/api/v2/acc/status'


# PATHS
LOG_FILE_PATH = os.path.join('logs', 'logs.log')
COGS_PATH = os.path.join('src', 'cogs')
DB_FILE_PATH = os.path.join('db', 'localdb.db')
DOCKER_VOLUME_PATH = '/data'

ROLES = {'DOURADINHO_GOD': 759023632051339264,
         'DOURADINHO_MESTRE': 759023197004890152,
         'DOURADINHO': 760530815456378981,
         'DOURA_HONORARIO': 882416521584975882,
         'DEV': 1171144045481959424
         }

PREMIUM_ROLES = {'ASSETO_PREMIUM': 1233745879945580635}

IMDB_API = os.getenv("CLOUDFLARE_WORKER")
api_key = os.getenv("CURRENCY_API_KEY")
CURRENCY_API = f'https://api.freecurrencyapi.com/v1/latest?apikey={api_key}'
CARD_API = 'https://www.deckofcardsapi.com/api'

# Configure the root logger

# Clear the log file
with open(LOG_FILE_PATH, 'w') as f:
    pass

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


def get_handler():
    return handler


def get_logger():
    return logger
