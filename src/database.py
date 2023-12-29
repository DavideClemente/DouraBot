import mysql.connector
from settings import DB_DATABASE, DB_HOST, DB_PASSWORD, DB_PORT, DB_USER, get_logger

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
            self.db: mysql.connector = mysql.connector.connect(database=DB_DATABASE,
                                                               user=DB_USER,
                                                               host=DB_HOST,
                                                               password=DB_PASSWORD,
                                                               port=DB_PORT)
        except mysql.connector.Error as e:
            logger.error(f'Error connecting to MariaDB Database: {e}')

    def get_connection(self) -> mysql.connector:
        if not self.db:
            raise ValueError('Database connection not established')
        return self.db
