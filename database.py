"""
Database layer for the Movie Recommender System.

Uses SQLite (via SQLAlchemy) to store:
- movies    : mirrors movie_list.pkl so the app no longer depends on unpickling
              a dataframe just to look up titles/ids. Row `id` is kept equal to
              the row's position in movie_list.pkl, since that position is also
              the index into the similarity matrix (similarity.pkl).
- users     : simple username/password accounts
- favorites : many-to-many link between users and movies (a user's watchlist)
- history   : log of what a user searched for and what was recommended

similarity.pkl itself (a dense ~N x N float matrix) is intentionally NOT moved
into the database — at a few thousand movies that's tens/hundreds of MB of
floats with no relational structure, so it's cheaper and simpler to keep it as
a flat file (pickle or .npy) and only use the DB for metadata + user data.

To swap SQLite for Postgres/MySQL later, just change DB_URL, e.g.:
    postgresql+psycopg2://user:password@host:5432/movie_app
Everything else (models, queries) stays the same.
"""

from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DB_URL = "sqlite:///movie_app.db"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)  # matches row order in similarity.pkl
    movie_id = Column(Integer, nullable=False)  # TMDB id, for posters (not unique — source data has dupes)
    title = Column(String, nullable=False, index=True)
    tags = Column(String)

    favorites = relationship("Favorite", back_populates="movie", cascade="all, delete-orphan")
    history_entries = relationship("History", back_populates="movie", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    history_entries = relationship("History", back_populates="user", cascade="all, delete-orphan")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_user_movie_fav"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    movie = relationship("Movie", back_populates="favorites")


class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)  # movie that was searched
    recommended_titles = Column(String)  # comma-separated snapshot of results shown
    searched_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="history_entries")
    movie = relationship("Movie", back_populates="history_entries")


def init_db():
    """Create tables if they don't exist yet. Safe to call every app startup."""
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
