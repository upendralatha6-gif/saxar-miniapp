import os
import logging
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")

@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_bookings (
                    id SERIAL PRIMARY KEY,
                    service VARCHAR(50) NOT NULL,
                    date VARCHAR(20) NOT NULL,
                    time VARCHAR(10) NOT NULL,
                    client_name VARCHAR(100) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    chat_id BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_reviews (
                    id SERIAL PRIMARY KEY,
                    booking_id INTEGER NOT NULL,
                    chat_id BIGINT NOT NULL,
                    client_name VARCHAR(100) NOT NULL,
                    service VARCHAR(50) NOT NULL,
                    date VARCHAR(20) NOT NULL,
                    stars INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_feedback_sent (
                    booking_id INTEGER PRIMARY KEY
                )
            """)
    logging.info("Database initialized.")

def _row_to_booking(row) -> dict:
    return {
        "service": row["service"],
        "date": row["date"],
        "time": row["time"],
        "client_name": row["client_name"],
        "phone": row["phone"],
        "chat_id": row["chat_id"],
    }

def add_booking(service, date, time, client_name, phone, chat_id) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO bot_bookings (service, date, time, client_name, phone, chat_id) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (service, date, time, client_name, phone, chat_id)
            )
            return cur.fetchone()[0]

def get_booking(booking_id: int) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM bot_bookings WHERE id = %s", (booking_id,))
            row = cur.fetchone()
            return _row_to_booking(row) if row else None

def get_all_bookings() -> list[tuple[int, dict]]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM bot_bookings ORDER BY id")
            return [(row["id"], _row_to_booking(row)) for row in cur.fetchall()]

def get_bookings_by_date(date: str) -> list[tuple[int, dict]]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM bot_bookings WHERE date = %s ORDER BY time", (date,))
            return [(row["id"], _row_to_booking(row)) for row in cur.fetchall()]

def get_booked_times(date: str) -> list[str]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT time FROM bot_bookings WHERE date = %s", (date,))
            return [row[0] for row in cur.fetchall()]

def get_bookings_by_chat_id(chat_id: int) -> list[tuple[int, dict]]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT * FROM bot_bookings WHERE chat_id = %s ORDER BY date, time",
                (chat_id,)
            )
            return [(row["id"], _row_to_booking(row)) for row in cur.fetchall()]

def get_all_client_chat_ids() -> set[int]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT chat_id FROM bot_bookings WHERE chat_id IS NOT NULL")
            return {row[0] for row in cur.fetchall()}

def delete_booking(booking_id: int) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "DELETE FROM bot_bookings WHERE id = %s RETURNING *",
                (booking_id,)
            )
            row = cur.fetchone()
            return _row_to_booking(row) if row else None

def add_review(booking_id, chat_id, client_name, service, date, stars) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO bot_reviews (booking_id, chat_id, client_name, service, date, stars) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (booking_id, chat_id, client_name, service, date, stars)
            )
            return cur.fetchone()[0]

def get_all_reviews() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM bot_reviews ORDER BY id DESC")
            return [dict(row) for row in cur.fetchall()]

def mark_feedback_sent(booking_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO bot_feedback_sent (booking_id) VALUES (%s) ON CONFLICT DO NOTHING",
                (booking_id,)
            )

def is_feedback_sent(booking_id: int) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM bot_feedback_sent WHERE booking_id = %s",
                (booking_id,)
            )
            return cur.fetchone() is not None
