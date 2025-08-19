import mysql.connector

class Database:
    def __init__(self):
        self.conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="tarun",
            database="face_attendance"
        )
        self.cursor = self.conn.cursor()

    def create(self, query, params=None):
        self.cursor.execute(query, params or ())
        self.conn.commit()

    def insert(self, query, params):
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor.lastrowid

    def read(self, query, params=None):
        self.cursor.execute(query, params or ())
        return self.cursor.fetchall()

    def close(self):
        self.cursor.close()
        self.conn.close()

# Initialize the database connection
conn = Database()