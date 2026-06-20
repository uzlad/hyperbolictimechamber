from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User's question or message")

class Evidence(BaseModel):
    movie_id: int
    title: str
    year: int | None

class ChatResponse(BaseModel):
    reply: str
    intent: str
    evidence: list[Evidence]


class GenreOut(BaseModel):
    id: int
    name: str


class MovieSummary(BaseModel):
    id: int
    title: str
    year: int | None
    genres: list[str]
    vote_average: float
    vote_count: int
    director: str | None


class CastMember(BaseModel):
    actor_name: str
    character: str | None

class MovieDetail(BaseModel):
    id: int
    title: str
    year: int | None
    release_date: str | None
    overview: str | None
    runtime: int | None
    original_language: str | None
    director: str | None
    vote_average: float
    vote_count: int
    genres: list[str]
    cast: list[CastMember]
