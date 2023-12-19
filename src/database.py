import sqlite3


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db = None
        return cls._instance

    def connect(self, filePath):
        self.db: sqlite3 = sqlite3.connect(filePath)

    def get_connection(self):
        if not self.db:
            raise ValueError('Database connection not established')
        return self.db
