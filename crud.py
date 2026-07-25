"""CRUD helper functions used by the Streamlit app."""

from database import get_session, Movie, Favorite, History


def get_all_titles():
    session = get_session()
    try:
        return [m.title for m in session.query(Movie).order_by(Movie.title).all()]
    finally:
        session.close()


def get_movie_by_title(title: str):
    session = get_session()
    try:
        return session.query(Movie).filter_by(title=title).first()
    finally:
        session.close()


def get_movie_by_id(movie_row_id: int):
    session = get_session()
    try:
        return session.query(Movie).filter_by(id=movie_row_id).first()
    finally:
        session.close()


def is_favorite(user_id: int, movie_row_id: int) -> bool:
    session = get_session()
    try:
        return (
            session.query(Favorite)
            .filter_by(user_id=user_id, movie_id=movie_row_id)
            .first()
            is not None
        )
    finally:
        session.close()


def add_favorite(user_id: int, movie_row_id: int):
    session = get_session()
    try:
        exists = session.query(Favorite).filter_by(user_id=user_id, movie_id=movie_row_id).first()
        if not exists:
            session.add(Favorite(user_id=user_id, movie_id=movie_row_id))
            session.commit()
    finally:
        session.close()


def remove_favorite(user_id: int, movie_row_id: int):
    session = get_session()
    try:
        fav = session.query(Favorite).filter_by(user_id=user_id, movie_id=movie_row_id).first()
        if fav:
            session.delete(fav)
            session.commit()
    finally:
        session.close()


def get_favorites(user_id: int):
    """Returns list of (movie_row_id, title) tuples."""
    session = get_session()
    try:
        favs = session.query(Favorite).filter_by(user_id=user_id).all()
        return [(f.movie.id, f.movie.title) for f in favs]
    finally:
        session.close()


def log_history(user_id: int, searched_movie_row_id: int, recommended_titles: list):
    session = get_session()
    try:
        entry = History(
            user_id=user_id,
            movie_id=searched_movie_row_id,
            recommended_titles=", ".join(recommended_titles),
        )
        session.add(entry)
        session.commit()
    finally:
        session.close()


def get_history(user_id: int, limit: int = 10):
    """Returns list of (searched_title, recommended_titles_str, timestamp) tuples, newest first."""
    session = get_session()
    try:
        entries = (
            session.query(History)
            .filter_by(user_id=user_id)
            .order_by(History.searched_at.desc())
            .limit(limit)
            .all()
        )
        return [(e.movie.title, e.recommended_titles, e.searched_at) for e in entries]
    finally:
        session.close()
