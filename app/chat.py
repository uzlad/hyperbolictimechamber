# pipeline: parse intent -> sqlite retreival -> json context -> llm -> ChatResponse
import json
import logging
import sqlite3

from app.intent import parse_intent
from app.llm import OllamaClient
from app.models import ChatResponse, Evidence
from app import repository

logger = logging.getLogger(__name__)

# System prompt i.e. consistent rules for the llm
SYSTEM_PROMPT = (
    "You are a movie expert. Answer the user's question using only the JSON "
    "context provided below. If the context doesn't contain what they're "
    "asking about, say so honestly rather than making something up. Keep "
    "replies short and conversational."
)

# Limit movies in context to prevent LLM from being overwhelmed and response short
MAX_CONTEXT_MOVIES = 8

# Takes message, parses intent, gets movies from sqlite, creates context then calls llm to get chatResponse
def handle_chat(
    message: str,
    conn: sqlite3.Connection,
    llm: OllamaClient,
) -> ChatResponse:
    intent = parse_intent(message)
    logger.info("Intent parsed: %s | genres=%s year=%s-%s rating>=%s fragment=%s",
                intent.intent, intent.genres, intent.year_from, intent.year_to,
                intent.min_rating, intent.title_fragment)

    movies: list[dict] = []

    if intent.intent == "recommend":
        movies = repository.recommend(
            conn,
            genres=intent.genres or None,
            year_from=intent.year_from,
            year_to=intent.year_to,
            min_rating=intent.min_rating,
            limit=MAX_CONTEXT_MOVIES,
        )

    elif intent.intent == "detail":
        if intent.title_fragment:
            movies = repository.find_by_title(conn, intent.title_fragment, limit=3)
        elif intent.genres or intent.year_from:
            movies = repository.recommend(
                conn,
                genres=intent.genres or None,
                year_from=intent.year_from,
                year_to=intent.year_to,
                limit=MAX_CONTEXT_MOVIES,
            )

    else:  # search
        if intent.title_fragment:
            movies = repository.find_by_title(conn, intent.title_fragment, limit=MAX_CONTEXT_MOVIES)
        elif intent.genres or intent.year_from:
            movies = repository.recommend(
                conn,
                genres=intent.genres or None,
                year_from=intent.year_from,
                year_to=intent.year_to,
                min_rating=intent.min_rating,
                limit=MAX_CONTEXT_MOVIES,
            )

    context_data = _build_context(movies)
    user_message = (
        f"User question: {message}\n\n"
        f"Movie database context (JSON):\n{context_data}"
    )

    try:
        reply = llm.chat(SYSTEM_PROMPT, user_message)
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        if movies:
            titles = ", ".join(m["title"] for m in movies[:5])
            reply = f"The model is unavailable right now, but I found these matches: {titles}."
        else:
            reply = "The model is unavailable right now and I couldn't find any matches in the database either."
    evidence = [
        Evidence(movie_id=m["id"], title=m["title"], year=m.get("year"))
        for m in movies
    ]

    return ChatResponse(reply=reply, intent=intent.intent, evidence=evidence)

# builds context for llm from movies retreived from sqlite and returns it as a json string
def _build_context(movies: list[dict]) -> str:
    slim = []
    for m in movies:
        cast_names = [c["actor_name"] for c in m.get("cast", [])]
        slim.append({
            "title": m["title"],
            "year": m.get("year"),
            "genres": m.get("genres", []),
            "director": m.get("director"),
            "cast": cast_names,
            "overview": (m.get("overview") or "")[:300],
            "vote_average": m.get("vote_average"),
        })
    return json.dumps(slim, indent=2) if slim else "[]"
