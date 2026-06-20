import re
from dataclasses import dataclass, field

# mapping from Lowercase phrase -> canonical TMDB genre name. 
# The first three are real aliases for scifi; rest are identity mappings so the parser can pick them up
# from freetext without subsequent normalisation step.
GENRE_ALIASES: dict[str, str] = {
    "sci-fi": "Science Fiction",
    "scifi": "Science Fiction",
    "science fiction": "Science Fiction",
    "action": "Action",
    "adventure": "Adventure",
    "animation": "Animation",
    "comedy": "Comedy",
    "crime": "Crime",
    "documentary": "Documentary",
    "drama": "Drama",
    "family": "Family",
    "fantasy": "Fantasy",
    "foreign": "Foreign",
    "history": "History",
    "horror": "Horror",
    "music": "Music",
    "mystery": "Mystery",
    "romance": "Romance",
    "thriller": "Thriller",
    "tv movie": "TV Movie",
    "war": "War",
    "western": "Western",
}

_RECOMMEND_PATTERN = re.compile(
    r"\b(recommend|suggest|show me|find me|give me|list|similar to|like)\b",
    re.IGNORECASE,
)
_DETAIL_PATTERN = re.compile(
    r"\b(tell me about|what is|what was|who directed|who starred|who is in|"
    r"cast of|director of|plot of|synopsis of|overview of|about the movie|"
    r"info on|information about)\b",
    re.IGNORECASE,
)
_YEAR_PATTERN = re.compile(r"\b(19[0-9]{2}|20[0-2][0-9])\b")
_YEAR_RANGE_PATTERN = re.compile(
    r"\b(from|since|after)\s+(19[0-9]{2}|20[0-2][0-9])\b.*?"
    r"\b(to|until|before|through)\s+(19[0-9]{2}|20[0-2][0-9])\b",
    re.IGNORECASE,
)
_RATING_PATTERN = re.compile(
    r"\b(?:rating|rated|score|above|over|at least|minimum)\s*([0-9](?:\.[0-9])?)\b",
    re.IGNORECASE,
)


@dataclass
class Intent:
    intent: str  # "recommend" | "detail" | "search"
    genres: list[str] = field(default_factory=list)
    year_from: int | None = None
    year_to: int | None = None
    title_fragment: str | None = None
    min_rating: float | None = None


def parse_intent(text: str) -> Intent:
    lower = text.lower()

    if _RECOMMEND_PATTERN.search(lower):
        intent_class = "recommend"
    elif _DETAIL_PATTERN.search(lower):
        intent_class = "detail"
    else:
        intent_class = "search"

    genres: list[str] = []
    for alias, canonical in GENRE_ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", lower) and canonical not in genres:
            genres.append(canonical)
            #re.escape handles special chars in aliases e.g. Marvel's Thunderbolts*

    year_from: int | None = None
    year_to: int | None = None
    range_match = _YEAR_RANGE_PATTERN.search(lower)
    if range_match:
        year_from = int(range_match.group(2))
        year_to = int(range_match.group(4))
    else:
        years = [int(y) for y in _YEAR_PATTERN.findall(text)]
        if len(years) == 1:
            year_from = years[0]
            year_to = years[0]
        elif len(years) >= 2:
            year_from, year_to = min(years), max(years)

    min_rating: float | None = None
    rating_match = _RATING_PATTERN.search(lower)
    if rating_match:
        min_rating = float(rating_match.group(1))

    title_fragment: str | None = None
    quoted = re.findall(r'["\']([^"\']+)["\']', text)
    if quoted:
        title_fragment = quoted[0]
    else:
        about_match = re.search(
            r"\b(?:about|called|titled|named|movie|film|directed|starring|cast of)\s+([A-Z][^,.?!]+)",
            text,
        )
        if about_match:
            fragment = about_match.group(1).strip()
            # drop trailing "and who starred in it" etc.
            fragment = re.sub(
                r"\s+(?:and|or|but|who|which|that)\b.*$", "", fragment, flags=re.IGNORECASE
            ).strip()
            title_fragment = fragment if fragment else None

    return Intent(
        intent=intent_class,
        genres=genres,
        year_from=year_from,
        year_to=year_to,
        title_fragment=title_fragment,
        min_rating=min_rating,
    )
