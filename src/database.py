import psycopg2
from settings import get_logger

logger = get_logger()


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db = None
        return cls._instance

    def connect(self):
        self.db: psycopg2 = psycopg2.connect(database='postgres',
                                             user='postgres',
                                             host='localhost',
                                             password='mysecretpassword',
                                             port=5432)

    def get_connection(self):
        if not self.db:
            raise ValueError('Database connection not established')
        return self.db
