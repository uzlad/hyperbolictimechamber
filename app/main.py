import logging
import sqlite3
import time
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.logging_conf import configure_logging
from app.config import settings
from app.db import get_connection
from app.llm import OllamaClient
from app.models import (
    ChatRequest, ChatResponse,
    GenreOut, MovieSummary, MovieDetail, CastMember,
)
from app import repository, chat as chat_module

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Movie Chat API",
    description="Ask natural-language questions about movies from the TMDB 5000 dataset.",
    version="0.1.0",
)


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s -> %d (%.1fms)", request.method, request.url.path,
                response.status_code, elapsed_ms)
    return response


def db_conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def llm_client():
    return OllamaClient()

DBConn = Annotated[sqlite3.Connection, Depends(db_conn)]
LLM = Annotated[OllamaClient, Depends(llm_client)]

#Adding redirect to docs for root path cuz root path is not informatve
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"])
def health(llm: LLM):
    return {
        "status": "ok",
        "model": settings.ollama_model,
        "ollama_available": llm.is_available(),
        "db": settings.db_path,
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(body: ChatRequest, conn: DBConn, llm: LLM):
    return chat_module.handle_chat(body.message, conn, llm)


@app.get("/genres", response_model=list[GenreOut], tags=["Movies"])
def genres(conn: DBConn):
    return repository.list_genres(conn)


@app.get("/movies", response_model=list[MovieSummary], tags=["Movies"])
def movies(
    conn: DBConn,
    genre: Annotated[str | None, Query()] = None,
    year: Annotated[int | None, Query()] = None,
    min_rating: Annotated[float | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    rows = repository.list_movies(conn, genre=genre, year=year, min_rating=min_rating, limit=limit)
    return [
        MovieSummary(
            id=r["id"],
            title=r["title"],
            year=r.get("year"),
            genres=r.get("genres", []),
            vote_average=r.get("vote_average", 0),
            vote_count=r.get("vote_count", 0),
            director=r.get("director"),
        )
        for r in rows
    ]


@app.get("/movies/{movie_id}", response_model=MovieDetail, tags=["Movies"])
def movie_detail(movie_id: int, conn: DBConn):
    row = repository.get_movie_detail(conn, movie_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found")
    return MovieDetail(
        id=row["id"],
        title=row["title"],
        year=row.get("year"),
        release_date=row.get("release_date"),
        overview=row.get("overview"),
        runtime=row.get("runtime"),
        original_language=row.get("original_language"),
        director=row.get("director"),
        vote_average=row.get("vote_average", 0),
        vote_count=row.get("vote_count", 0),
        genres=row.get("genres", []),
        cast=[
            CastMember(actor_name=c["actor_name"], character=c.get("character"))
            for c in row.get("cast", [])
        ],
    )
