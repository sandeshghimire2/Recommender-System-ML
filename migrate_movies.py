"""
One-time migration: load movies from movie_list.pkl (produced by model.ipynb)
into the `movies` table so the Streamlit app reads metadata from the database
instead of unpickling a dataframe every run.

Run this once, after model.ipynb has produced movie_list.pkl and similarity.pkl
in the same folder as this script:

    python migrate_movies.py

Re-running it is safe — it skips migration if the movies table is already
populated. Delete movie_app.db if you want to redo it from scratch.
"""

import pickle

from database import init_db, get_session, Movie


def migrate(pickle_path: str = "movie_list.pkl"):
    init_db()
    movies_df = pickle.load(open(pickle_path, "rb"))

    session = get_session()
    try:
        existing = session.query(Movie).count()
        if existing > 0:
            print(f"movies table already has {existing} rows — skipping migration.")
            return

        rows = []
        for idx, row in movies_df.reset_index(drop=True).iterrows():
            rows.append(
                Movie(
                    id=idx,  # keep row order identical to similarity.pkl's index
                    movie_id=int(row["movie_id"]),
                    title=row["title"],
                    tags=row["tags"] if "tags" in row else "",
                )
            )
        session.bulk_save_objects(rows)
        session.commit()
        print(f"Inserted {len(rows)} movies into the database.")
    finally:
        session.close()


if __name__ == "__main__":
    migrate()
