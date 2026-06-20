from app import repository

def test_find_by_title(db):
    results = repository.find_by_title(db, "Inception")
    assert len(results) == 1
    assert results[0]["title"] == "Inception"
    assert any(c["actor_name"] == "Leonardo DiCaprio" for c in results[0]["cast"])

def test_recommend_filters(db):
    results = repository.recommend(db, genres=["Action"], year_from=2008, year_to=2010, limit=10)
    assert all(r["year"] in range(2008, 2011) for r in results)

def test_get_movie_detail(db):
    detail = repository.get_movie_detail(db, 1)
    assert detail["title"] == "Inception"
    assert "Action" in detail["genres"] or "Science Fiction" in detail["genres"]
    assert any(c["actor_name"] == "Leonardo DiCaprio" for c in detail["cast"])

def test_get_movie_detail_not_found(db):
    assert repository.get_movie_detail(db, 99999) is None
