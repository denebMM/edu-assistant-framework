import psycopg2
import os

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        dbname=os.getenv('DB_NAME')
    )
    return conn

def log_metric(assistant_type, latency, error_rate, user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO metrics (assistant_type, latency, error_rate, user_id)
        VALUES (%s, %s, %s, %s)
    """, (assistant_type, latency, error_rate, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_or_create_user(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO users (username) VALUES (%s) RETURNING id", (username,))
        user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return user[0]