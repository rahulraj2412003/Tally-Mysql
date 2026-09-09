from backend.database.connection import get_mysql_connection

connection = get_mysql_connection()

print("Connected to MySQL successfully!")

connection.close()
