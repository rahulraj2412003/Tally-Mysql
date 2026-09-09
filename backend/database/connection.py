"""Single MySQL connection factory for services and future API routes."""

import mysql.connector
from mysql.connector import MySQLConnection

from backend.config import settings


def get_mysql_connection() -> MySQLConnection:
    return mysql.connector.connect(**settings.mysql_config)


def test_mysql_connection() -> None:
    connection = get_mysql_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
    finally:
        connection.close()

