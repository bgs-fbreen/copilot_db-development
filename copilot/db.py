"""
Database connection handler for Copilot
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def execute_query(query, params=None, fetch=True):
    """Execute a query and return results"""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            conn.commit()
            return None
    finally:
        conn.close()

def execute_insert(query, params=None):
    """Execute an INSERT and return the new row ID"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            if cur.rowcount > 0:
                return cur.fetchone()[0] if cur.description else None
    finally:
        conn.close()
