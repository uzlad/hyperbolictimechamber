import sqlite3

# MVC to avoid high rated but obscure films surfacing first
MIN_VOTE_COUNT = 50

def list_genres(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT id, name FROM genres ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def find_by_title(
    conn: sqlite3.Connection,
    fragment: str,
    limit: int = 10,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT m.id, m.title, m.year, m.overview, m.director,
               m.vote_average, m.vote_count,
               GROUP_CONCAT(g.name, ', ') AS genres
          FROM movies m
          LEFT JOIN movie_genres mg ON mg.movie_id = m.id
          LEFT JOIN genres g        ON g.id = mg.genre_id
         WHERE m.title LIKE ? COLLATE NOCASE
         GROUP BY m.id
         ORDER BY m.vote_count DESC
         LIMIT ?
        """,
        (f"%{fragment}%", limit),
    ).fetchall()
    return _rows_with_cast(conn, rows)


def recommend(
    conn: sqlite3.Connection,
    genres: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    min_rating: float | None = None,
    limit: int = 10,
) -> list[dict]:
    params: list = []
    conditions = [f"m.vote_count >= {MIN_VOTE_COUNT}"]

    if genres:
        placeholders = ",".join("?" * len(genres))
        conditions.append(
            f"m.id IN ("
            f"  SELECT movie_id FROM movie_genres mg2"
            f"  JOIN genres g2 ON g2.id = mg2.genre_id"
            f"  WHERE g2.name IN ({placeholders})"
            f")"
        )
        params.extend(genres)

    if year_from is not None:
        conditions.append("m.year >= ?")
        params.append(year_from)

    if year_to is not None:
        conditions.append("m.year <= ?")
        params.append(year_to)

    if min_rating is not None:
        conditions.append("m.vote_average >= ?")
        params.append(min_rating)

    where = " AND ".join(conditions)
    params.append(limit)

    rows = conn.execute(
        f"""
        SELECT m.id, m.title, m.year, m.overview, m.director,
               m.vote_average, m.vote_count,
               GROUP_CONCAT(g.name, ', ') AS genres
          FROM movies m
          LEFT JOIN movie_genres mg ON mg.movie_id = m.id
          LEFT JOIN genres g        ON g.id = mg.genre_id
         WHERE {where}
         GROUP BY m.id
         ORDER BY m.vote_average DESC, m.vote_count DESC
         LIMIT ?
        """,
        params,
    ).fetchall()
    return _rows_with_cast(conn, rows)


def get_movie_detail(conn: sqlite3.Connection, movie_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT m.id, m.title, m.year, m.release_date, m.overview, m.runtime,
               m.original_language, m.director, m.vote_average, m.vote_count,
               GROUP_CONCAT(g.name, ', ') AS genres
          FROM movies m
          LEFT JOIN movie_genres mg ON mg.movie_id = m.id
          LEFT JOIN genres g        ON g.id = mg.genre_id
         WHERE m.id = ?
         GROUP BY m.id
        """,
        (movie_id,),
    ).fetchone()

    if row is None:
        return None

    result = dict(row)
    result["genres"] = [g.strip() for g in (result["genres"] or "").split(",") if g.strip()]
    result["cast"] = _get_cast(conn, movie_id)
    return result


def list_movies(
    conn: sqlite3.Connection,
    genre: str | None = None,
    year: int | None = None,
    min_rating: float | None = None,
    limit: int = 20,
) -> list[dict]:
    return recommend(
        conn,
        genres=[genre] if genre else None,
        year_from=year,
        year_to=year,
        min_rating=min_rating,
        limit=limit,
    )

#Helper
def _get_cast(conn: sqlite3.Connection, movie_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT actor_name, character FROM cast WHERE movie_id = ? ORDER BY ord LIMIT 5",
        (movie_id,),
    ).fetchall()
    return [{"actor_name": r["actor_name"], "character": r["character"]} for r in rows]

#Helper
def _rows_with_cast(conn: sqlite3.Connection, rows) -> list[dict]:
    results = []
    for row in rows:
        d = dict(row)
        d["genres"] = [g.strip() for g in (d.get("genres") or "").split(",") if g.strip()]
        d["cast"] = _get_cast(conn, d["id"])
        results.append(d)
    return results
