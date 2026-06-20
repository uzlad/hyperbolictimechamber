import sqlite3
import os
from app.config import settings


CREATE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS movies (
        id              INTEGER PRIMARY KEY,
        title           TEXT    NOT NULL,
        year            INTEGER,
        release_date    TEXT,
        overview        TEXT,
        runtime         INTEGER,
        original_language TEXT,
        director        TEXT,
        vote_average    REAL    DEFAULT 0,
        vote_count      INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS genres (
        id   INTEGER PRIMARY KEY,
        name TEXT    NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS movie_genres (
        movie_id INTEGER NOT NULL REFERENCES movies(id),
        genre_id INTEGER NOT NULL REFERENCES genres(id),
        PRIMARY KEY (movie_id, genre_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cast (
        movie_id     INTEGER NOT NULL REFERENCES movies(id),
        actor_name   TEXT    NOT NULL,
        character    TEXT,
        ord          INTEGER,
        PRIMARY KEY (movie_id, actor_name)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_movies_year         ON movies(year)",
    "CREATE INDEX IF NOT EXISTS idx_movies_title        ON movies(title COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_movie_genres_genre  ON movie_genres(genre_id)",
    "CREATE INDEX IF NOT EXISTS idx_cast_movie          ON cast(movie_id)",
]


def init_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    for stmt in CREATE_STATEMENTS:
        conn.execute(stmt)
    conn.commit()


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or settings.db_path
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row # to access columns by name
    conn.execute("PRAGMA foreign_keys = ON") #off by default
    return conn
