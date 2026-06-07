import psycopg2
import psycopg2.extras

from . import config

conn = psycopg2.connect(
    dbname=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    host=config.DB_HOST,
    port=config.DB_PORT,
    application_name="plane-notify-delayed",
)


def cursor() -> psycopg2.extras.DictCursor:
    """Return a new DictCursor on the shared connection."""
    return conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
