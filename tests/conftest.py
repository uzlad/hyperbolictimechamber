import sqlite3
import pytest
from app.db import init_schema


@pytest.fixture
def db():
    """In-memory SQLite database seeded with a handful of movies."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)

    #Genres
    conn.executemany(
        "INSERT INTO genres (id, name) VALUES (?, ?)",
        [(28, "Action"), (12, "Adventure"), (878, "Science Fiction"), (18, "Drama"), (35, "Comedy")],
    )

    #Movies
    movies = [
        (1, "Inception",         2010, "2010-07-16", "A thief who steals corporate secrets through dream-sharing technology.", 148, "en", "Christopher Nolan", 8.3, 22000),
        (2, "The Matrix",        1999, "1999-03-31", "A hacker discovers the world is a simulation.",                         136, "en", "Lana Wachowski",    8.7, 18000),
        (3, "Interstellar",      2014, "2014-11-07", "Astronauts travel through a wormhole in search of a new home.",        169, "en", "Christopher Nolan", 8.6, 25000),
        (4, "The Dark Knight",   2008, "2008-07-18", "Batman faces the Joker in Gotham City.",                              152, "en", "Christopher Nolan", 9.0, 27000),
        (5, "Superbad",          2007, "2007-08-17", "Two high school friends try to get alcohol for a party.",             113, "en", "Greg Mottola",      7.6,  8000),
        (6, "The Amazing Spider-Man", 2012, "2012-07-03", "A teenage outcast Peter Parker begins to unravel the mystery of his past.", 136, "en", "Marc Webb",         7.0, 12000),
    ]
    conn.executemany(
        "INSERT INTO movies (id, title, year, release_date, overview, runtime, "
        "original_language, director, vote_average, vote_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        movies,
    )

    # movie_genres
    conn.executemany(
        "INSERT INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
        [(1, 28), (1, 878), (2, 28), (2, 878), (3, 12), (3, 878), (4, 28), (5, 35), (6, 28)],

    )

    # Cast
    cast = [
        (1, "Leonardo DiCaprio", "Dom Cobb",       0),
        (1, "Joseph Gordon-Levitt", "Arthur",      1),
        (2, "Keanu Reeves",      "Neo",            0),
        (2, "Laurence Fishburne","Morpheus",       1),
        (3, "Matthew McConaughey","Cooper",        0),
        (4, "Christian Bale",   "Bruce Wayne",     0),
        (6, "Andrew Garfield",  "Peter Parker",    0),
        (6, "Emma Stone",       "Gwen Stacy",       1),
    ]
    conn.executemany(
        "INSERT INTO cast (movie_id, actor_name, character, ord) VALUES (?, ?, ?, ?)",
        cast,
    )
    conn.commit()

    yield conn
    conn.close()
