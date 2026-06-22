# database/db_connection.py
# Handles all MySQL connection logic and raw query execution.
# Every other file imports from here — nothing else talks to MySQL directly.

import mysql.connector
import pandas as pd
from contextlib import contextmanager

# ─────────────────────────────────────────────
# UPDATE THESE TO MATCH YOUR MYSQL SETUP
# ─────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "database": "ekitchen",
    "user":     "root",
    "password": "aish239"   
}


def test_connection():

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        conn.close()
        return True, None
    except mysql.connector.Error as e:
        code = e.errno
        if code == 1045:
            msg = "Wrong username or password.\n\nFix: Open database/db_connection.py and update 'user' and 'password'."
        elif code == 2003:
            msg = "Cannot reach MySQL at localhost:3306.\n\nFix: Start MySQL.\n• Windows: Services → MySQL → Start\n• Or run: net start mysql"
        elif code == 1049:
            msg = "Database 'ekitchen' not found.\n\nFix: Run setup.py first — python database/setup.py"
        else:
            msg = f"MySQL error {code}: {e.msg}"
        return False, msg
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


@contextmanager
def get_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_query(sql, params=None):
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=params)


def run_write(sql, params=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.rowcount


def run_write_returning(sql, params=None):
    """Run INSERT → returns the auto-generated ID of the new row."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.lastrowid
