import mysql.connector
from mysql.connector import pooling
from settings import DB_DATABASE, DB_HOST, DB_PASSWORD, DB_PORT, DB_USER, get_logger

logger = get_logger()


class DatabaseManager:
    _instance = None
    _pool = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db = None
            cls._instance.create_pool()
        return cls._instance

    def create_pool(self):
        try:
            self._pool = pooling.MySQLConnectionPool(
                pool_name="dourapool",
                pool_size=10,
                database=DB_DATABASE,
                user=DB_USER,
                host=DB_HOST,
                password=DB_PASSWORD,
                port=DB_PORT
            )
        except mysql.connector.Error as e:
            logger.error(f'Error creating connection pool: {e}')

    def get_connection(self) -> mysql.connector:
        if not self._pool:
            raise ValueError('Connection pool not created')
        try:
            # Get a connection from the pool
            connection = self._pool.get_connection()
        except mysql.connector.Error as e:
            logger.error(f'Error getting connection from pool: {e}')
            raise
        return connection
