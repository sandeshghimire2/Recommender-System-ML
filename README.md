# Movie Recommender — now with a database

## What changed vs. your original `streamlit.py`

Your original app loaded `movie_list.pkl` and `similarity.pkl` straight into
memory every run, and had no concept of users. This version adds a SQLite
database (`movie_app.db`, created automatically) with four tables:

| Table       | Purpose                                                         |
|-------------|------------------------------------------------------------------|
| `movies`    | Title + TMDB id for each movie (replaces reading titles from the pickle) |
| `users`     | Username + bcrypt-hashed password                                |
| `favorites` | Which movies each user has saved to their watchlist              |
| `history`   | What each user searched for and what was recommended, with a timestamp |

`similarity.pkl` (the cosine-similarity matrix) is still kept as a pickle
file — it's a dense matrix of floats with no relational structure, so a SQL
table doesn't help there. The `movies` table's `id` column is deliberately
kept identical to each movie's row position in `movie_list.pkl`/`similarity.pkl`,
so the two stay in sync.

## Files

- `database.py` — SQLAlchemy models (`Movie`, `User`, `Favorite`, `History`) and DB setup
- `migrate_movies.py` — one-time script that loads `movie_list.pkl` into the `movies` table
- `auth.py` — signup / login (bcrypt password hashing)
- `crud.py` — all the database read/write helpers the app uses
- `streamlit_app.py` — the app itself: login screen, movie picker, recommendations, favorites, history

## Setup

1. Put these files in the same folder as the `movie_list.pkl` and
   `similarity.pkl` produced by your `model.ipynb`.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the one-time migration to load movie metadata into the database:
   ```
   python migrate_movies.py
   ```
   This creates `movie_app.db` and populates the `movies` table. Safe to
   re-run — it skips itself if already populated.
4. Launch the app:
   ```
   streamlit run streamlit_app.py
   ```
5. Sign up for an account on first launch, then log in. Search for a movie,
   click "Show Recommendation", and use the ❤️ button under each result to
   save it to your favorites. Your sidebar shows your favorites and your
   last 5 searches.

## Notes / next steps

- **TMDB API key**: it's currently hardcoded (as it was in your original
  file) for convenience. For anything beyond local testing, move it to
  `st.secrets["TMDB_API_KEY"]` and read it from there instead.
- **Switching databases**: everything goes through SQLAlchemy, so moving
  from SQLite to Postgres/MySQL later is just a one-line change to `DB_URL`
  in `database.py` — no query code needs to change.
- **Passwords**: hashed with bcrypt, never stored in plaintext.
- This is intentionally a simple, dependency-light auth setup (no email
  verification, password reset, etc.) — enough for a personal/demo project,
  not a production auth system.
