import sqlite3
from settings import get_logger

logger = get_logger()


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db = None
        return cls._instance

    def connect(self, filePath):
        self.db: sqlite3 = sqlite3.connect(filePath)
        try:
            with self.db:
                self.db.execute(
                    'CREATE TABLE IF NOT EXISTS BIRTHDAYS(USER_ID INTEGER PRIMARY KEY, USERNAME TEXT NOT NULL UNIQUE, BIRTH_DATE TEXT NOT NULL)')
        except Exception as e:
            logger.info(e)

    def get_connection(self) -> sqlite3:
        if not self.db:
            raise ValueError('Database connection not established')
        return self.db
