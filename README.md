# Movie Chat API (hyperbolictimechamber)

A REST API that lets you ask NLQs about movies. 
It queries a local SQLite database built from the TMDB 5000 dataset.
Uses Ollama (`llama3.2:3b`) to generate conversational responses based on what it finds.

---

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/download/) installed and running

---

## Setup

```bash
git clone <repo-url>
cd hyperbolictimechamber
pip install -r requirements.txt
```

Start Ollama, then pull the model (~2 GB):

```bash
ollama pull llama3.2:3b
```

Load the dataset. 
Script expects the TMDB CSVs ([Kaggle: TMDB 5000 Movie Dataset](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata)) one directory up in a `TMDB5000/` folder.

```bash
python scripts/load_data.py
# Done. Inserted 4803 movies, 20 genres, 23594 cast rows.
```

Custom paths if needed:

```bash
python scripts/load_data.py --movies /path/to/tmdb_5000_movies.csv \
                             --credits /path/to/tmdb_5000_credits.csv
```

Start the server (make sure Ollama is running first):

```bash
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`. Docs (interactive) at `http://localhost:8000/docs`.

Environment variables (all optional, defaults shown):

| Variable | Default |
|---|---|
| `OLLAMA_URL` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `llama3.2:3b` |
| `DB_PATH` | `data/movies.db` |

Set any of these in your shell before running (`$env:OLLAMA_MODEL = "..."` on PowerShell, `export OLLAMA_MODEL=...` on bash). `.env.example` documents the supported variables.

---

## Tests

```bash
pytest tests/ -v
```

All 13 tests use an in-memory SQLite fixture - i.e. Ollama doesn't need to be running.

---

## API

### `GET /health`

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "model": "llama3.2:3b",
  "ollama_available": true,
  "db": "data/movies.db"
}
```

### `POST /chat`

Send a question and get a conversational reply.
The response also includes `intent` (what the parser classified the query as) and `evidence` (the DB rows passed to the LLM as context).

```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "tell me about Inception"}'
```

```json
{
  "reply": "Inception (2010) is a science fiction thriller directed by Christopher Nolan. It follows Dom Cobb, a thief who steals corporate secrets through dream-sharing. Stars Leonardo DiCaprio, with a vote average of 8.1.",
  "intent": "detail",
  "evidence": [
    { "movie_id": 27205, "title": "Inception", "year": 2010 }
  ]
}
```

```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "recommend action movies from 2012 with rating above 7"}'
```

```json
{
  "reply": "Here are some well-rated action films from 2012: The Avengers (8.1), The Dark Knight Rises (7.9), and Skyfall (7.7).",
  "intent": "recommend",
  "evidence": [
    { "movie_id": 24428, "title": "The Avengers", "year": 2012 },
    { "movie_id": 49026, "title": "The Dark Knight Rises", "year": 2012 }
  ]
}
```

```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "who directed The Matrix?"}'
```

```json
{
  "reply": "The Matrix (1999) was directed by Lana Wachowski. It stars Keanu Reeves as Neo and has a vote average of 8.1.",
  "intent": "detail",
  "evidence": [
    { "movie_id": 603, "title": "The Matrix", "year": 1999 }
  ]
}
```

### Example Terminal Output
<img width="1607" height="402" alt="image" src="https://github.com/user-attachments/assets/023ab8a9-4644-4618-9c08-05db5fc9005c" />


### `GET /movies`

Filter and list movies. All params are optional.

| Param | Type | Example |
|---|---|---|
| `genre` | string | `Action` |
| `year` | integer | `2010` |
| `min_rating` | float | `8.0` |
| `limit` | integer (1–100) | `10` |

```bash
curl "http://localhost:8000/movies?genre=Thriller&min_rating=8&limit=5"
```

### `GET /movies/{movie_id}`

Full detail for a single movie including cast, genres, and overview.

```bash
curl http://localhost:8000/movies/27205
```

### `GET /genres`

List all genres in the database.

---

## How it works

When a request hits `POST /chat`, three things happen:

1. **Intent parsing** (`intent.py`) - a regex-based parser classifies the message as `recommend`, `detail`, or `search`, and pulls out any entities mentioned: genre, year range, title and minimum rating.

2. **DB lookup** (`repository.py`) - based on the intent, the relevant SQL query runs against SQLite and returns up to 8 matching movies with their genres and cast.

3. **LLM response** (`chat.py` + `llm.py`) - the retrieved movies are serialised to JSON and injected into the system prompt. The LLM is told to answer only from that context, which keeps responses grounded and makes it easy to spot when retrieval missed something (the `evidence` field shows exactly what was passed in).

Went with plain `sqlite3` over an ORM because there are only 4 tables and the queries are straightforward - easier to reason about and explain. 
Intent parsing is rule-based rather than ML-based for the same reason; it covers the query patterns in scope without adding a model dependency. 
The obvious future work would be vector/semantic-search for similarity queries and streaming responses from Ollama....S

---

## What's not finished

A few things that are perhaps "missing":

The challenge doc asks for separate tables for movies, genres and ratings. I have movies and genres (plus a `movie_genres` link table and a `cast` table), but no standalone ratings table. TMDB only provides aggregated ratings, so I put `vote_average` and `vote_count` as columns on `movies`. A ratings table with one row per movie would be there just to tick a box. MovieLens is probably optimal for this use case as I'd have proper per-user ratings and the table would be more appropriate.

The intent parser is regex. It handles the example queries in the doc and plenty of variations around them, but it falls over on anything off-script, e.g. asking it about a person ("tell me about Christopher Nolan") - it'll have no concept of person entities, only titles. An LLM-based classifier would be the proper fix or NER.

Title matching is `LIKE '%X%'`, so "tell me about The Dark Knight" pulls back the original plus *Rises* and the animated *Returns*. The LLM picks the right one from context, but ranking exact matches first would be a quick win.

First request is slow (~30-60s) while the model warms up; subsequent ones are 5–10s. Streaming responses would help the UX a lot.
`/chat` is stateless - no conversation memory, scoped out on purpose to keep the solution small, but a `session_id` + in-memory dict would allow for basic memory.

Typically, I'd add auth, rate limiting and Docker containerisation, but no need for that in this challenge.
