import mysql.connector
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
        try:
            self.db: mysql.connector = mysql.connector.connect(database='master',
                                                               user='dourabot',
                                                               host='localhost',
                                                               password='dourabot123',
                                                               port=3306)
        except mysql.connector.Error as e:
            logger.error(f'Error connecting to MariaDB Database: {e}')

    def get_connection(self) -> mysql.connector:
        if not self.db:
            raise ValueError('Database connection not established')
        return self.db
