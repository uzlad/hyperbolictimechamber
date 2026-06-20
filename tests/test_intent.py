from app.intent import parse_intent

def test_recommend_intent():
    result = parse_intent("recommend some action movies")
    assert result.intent == "recommend"
    assert "Action" in result.genres

def test_detail_intent():
    result = parse_intent("tell me about Inception")
    assert result.intent == "detail"
    assert result.title_fragment == "Inception"

def test_search_fallback_with_year():
    result = parse_intent("Interstellar 2014")
    assert result.intent == "search"
    assert result.year_from == 2014

def test_min_rating_extraction():
    result = parse_intent("recommend movies rated above 8")
    assert result.min_rating == 8.0


def test_scifi_alias():
    result = parse_intent("suggest some sci-fi films")
    assert "Science Fiction" in result.genres

def test_directed_title_extraction():
    # regression: "who directed bananas and...?" should extract bananas, not the full clause
    result = parse_intent("who directed Interstellar and who starred in it?")
    assert result.intent == "detail"
    assert result.title_fragment == "Interstellar"
