from dotenv import load_dotenv
import os
from logging.config import dictConfig
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

# LOGGING_CONFIG = {
#     "version": 1,
#     "disabled_existing_loggers": False,
#     "formatters": {
#         "verbose": {
#             "format": "%(levelname)-10s - %(asctime)s - %(module)-15s : %(message)s"
#         },
#         "standard": {"format": "%(levelname)-10s - %(name)-15s : %(message)s"},
#     },
#     "handlers": {
#         "console": {
#             "level": "DEBUG",
#             "class": "logging.StreamHandler",
#             "formatter": "standard",
#         },
#         "console2": {
#             "level": "WARNING",
#             "class": "logging.StreamHandler",
#             "formatter": "standard",
#         },
#         "file": {
#             "level": "INFO",
#             "class": "logging.FileHandler",
#             "filename": LOG_FILE_PATH,
#             "mode": "w",
#             "formatter": "verbose",
#         },
#     },
#     "loggers": {
#         "bot": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
#         "discord": {
#             "handlers": ["console2", "file"],
#             "level": "INFO",
#             "propagate": False,
#         },
#     },
# }

# dictConfig(LOGGING_CONFIG)
