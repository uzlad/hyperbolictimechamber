# Load TMDB 5000 CSVs into SQLite.
# Usage: python scripts/load_data.py [--movies path] [--credits path] [--db path]
import argparse
import json
import logging
import os
import sqlite3
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Go to parent dir

from app.db import init_schema, get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d@%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_MOVIES_CSV = os.path.join(
    os.path.dirname(__file__), "..", "..", "TMDB5000", "tmdb_5000_movies.csv"
)
DEFAULT_CREDITS_CSV = os.path.join(
    os.path.dirname(__file__), "..", "..", "TMDB5000", "tmdb_5000_credits.csv"
)
DEFAULT_DB = "data/movies.db"


def _parse_json_column(value: str) -> list:
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []

def _extract_year(release_date: str) -> int | None:
    if release_date and len(release_date) >= 4:
        try:
            return int(release_date[:4])
        except ValueError:
            pass
    return None


def _extract_director(crew: list) -> str | None:
    for member in crew:
        if member.get("job") == "Director":
            return member.get("name")
    return None


def load(movies_csv: str, credits_csv: str, db_path: str) -> None:
    logger.info("Reading credits from %s", credits_csv)
    credits: dict[int, dict] = {}
    with open(credits_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            movie_id = int(row["movie_id"])
            cast_list = _parse_json_column(row.get("cast", ""))
            crew_list = _parse_json_column(row.get("crew", ""))
            credits[movie_id] = {
                "cast": cast_list[:5], #5 cast member max
                "director": _extract_director(crew_list),
            }

    logger.info("Connecting to database %s", db_path)
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)

    conn = sqlite3.connect(db_path)
    #FKs off for the drop+rebuild; init_schema turns them back on to be safe.
    conn.execute("PRAGMA foreign_keys = OFF")

    # Drop and recreate so re-running this script is idempotent
    logger.info("Dropping existing tables…")
    for tbl in ("cast", "movie_genres", "genres", "movies"):
        conn.execute(f"DROP TABLE IF EXISTS {tbl}")
    conn.commit()

    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)

    logger.info("Reading movies from %s", movies_csv)
    movie_count = 0
    genre_map: dict[int, str] = {}
    cast_rows: list[tuple] = []
    movie_genre_rows: list[tuple] = []

    with open(movies_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                movie_id = int(row["id"])
            except (ValueError, KeyError):
                continue

            year = _extract_year(row.get("release_date", ""))
            runtime_raw = row.get("runtime", "")
            try:
                runtime = int(float(runtime_raw)) if runtime_raw else None
            except ValueError:
                runtime = None
            vote_raw = row.get("vote_average", "0")
            try:
                vote_average = float(vote_raw) if vote_raw else 0.0
            except ValueError:
                vote_average = 0.0
            vote_count_raw = row.get("vote_count", "0")
            try:
                vote_count = int(vote_count_raw) if vote_count_raw else 0
            except ValueError:
                vote_count = 0

            cred = credits.get(movie_id, {})
            director = cred.get("director")

            conn.execute(
                """
                INSERT OR REPLACE INTO movies
                  (id, title, year, release_date, overview, runtime,
                   original_language, director, vote_average, vote_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    movie_id,
                    row.get("title", ""),
                    year,
                    row.get("release_date"),
                    row.get("overview"),
                    runtime,
                    row.get("original_language"),
                    director,
                    vote_average,
                    vote_count,
                ),
            )
            movie_count += 1

            for g in _parse_json_column(row.get("genres", "")):
                gid = g.get("id")
                gname = g.get("name")
                if gid and gname:
                    genre_map[gid] = gname
                    movie_genre_rows.append((movie_id, gid))

            for order, member in enumerate(cred.get("cast", [])):
                name = member.get("name")
                character = member.get("character")
                if name:
                    cast_rows.append((movie_id, name, character, order))

    for gid, gname in genre_map.items():
        conn.execute("INSERT OR IGNORE INTO genres (id, name) VALUES (?, ?)", (gid, gname))

    conn.executemany(
        "INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
        movie_genre_rows,
    )

    conn.executemany(
        "INSERT OR IGNORE INTO cast (movie_id, actor_name, character, ord) VALUES (?, ?, ?, ?)",
        cast_rows,
    )

    conn.commit()
    conn.close()

    logger.info(
        "Done. Inserted %d movies, %d genres, %d cast rows.",
        movie_count,
        len(genre_map),
        len(cast_rows),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load TMDB 5000 data into SQLite")
    parser.add_argument("--movies",  default=DEFAULT_MOVIES_CSV, help="Path to tmdb_5000_movies.csv")
    parser.add_argument("--credits", default=DEFAULT_CREDITS_CSV, help="Path to tmdb_5000_credits.csv")
    parser.add_argument("--db",      default=DEFAULT_DB,         help="Output SQLite database path")
    args = parser.parse_args()

    for path, label in [(args.movies, "movies CSV"), (args.credits, "credits CSV")]:
        if not os.path.exists(path):
            logger.error("Cannot find %s at: %s", label, os.path.abspath(path))
            sys.exit(1)

    load(args.movies, args.credits, args.db)


if __name__ == "__main__":
    main()
