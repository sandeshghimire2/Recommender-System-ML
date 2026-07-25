import requests
import streamlit as st
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from database import init_db, get_session, Movie
from auth import register_user, authenticate_user
from crud import (
    get_all_titles,
    get_movie_by_title,
    get_movie_by_id,
    add_favorite,
    remove_favorite,
    is_favorite,
    get_favorites,
    log_history,
    get_history,
)

st.set_page_config(page_title="Movie Recommender", layout="wide")

TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"  # move to st.secrets for production use


@st.cache_resource
def load_similarity():
    """
    Build the similarity matrix at runtime from the `tags` column already
    stored in the movies table, instead of unpickling a precomputed
    similarity.pkl. A dense N x N similarity.pkl gets too large to push to
    GitHub (Streamlit Cloud pulls the repo directly), while `tags` text is
    tiny by comparison. Cached via st.cache_resource so this only runs once
    per app instance, not on every rerun.

    NOTE: relies on Movie.id being a contiguous 0..N-1 sequence matching the
    original row order (see migrate_movies.py), so ordering by id here
    reproduces the same row/column alignment the old similarity.pkl had.
    """
    session = get_session()
    try:
        movies = session.query(Movie).order_by(Movie.id).all()
        tags = [m.tags or "" for m in movies]
    finally:
        session.close()

    cv = CountVectorizer(max_features=5000, stop_words="english")
    vectors = cv.fit_transform(tags).toarray()
    return cosine_similarity(vectors)


def fetch_poster(movie_id):
    url = (
        f"https://api.themoviedb.org/3/movie/{movie_id}"
        f"?api_key={TMDB_API_KEY}&language=en-US"
    )
    try:
        data = requests.get(url, timeout=5).json()
        poster_path = data.get("poster_path")
        if not poster_path:
            return "https://via.placeholder.com/500x750?text=No+Poster"
        return "https://image.tmdb.org/t/p/w500/" + poster_path
    except requests.RequestException:
        return "https://via.placeholder.com/500x750?text=No+Poster"


def recommend(movie_title, similarity):
    movie = get_movie_by_title(movie_title)
    if not movie:
        return [], [], []

    distances = sorted(
        list(enumerate(similarity[movie.id])), reverse=True, key=lambda x: x[1]
    )

    names, posters, row_ids = [], [], []
    for row_id, _score in distances[1:6]:
        rec = get_movie_by_id(row_id)
        if rec is None:
            continue
        names.append(rec.title)
        posters.append(fetch_poster(rec.movie_id))
        row_ids.append(rec.id)
    return names, posters, row_ids


def login_screen():
    st.header("🎬 Movie Recommender")
    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log in"):
            user_id = authenticate_user(username, password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab_signup:
        new_username = st.text_input("Choose a username", key="signup_user")
        new_password = st.text_input("Choose a password", type="password", key="signup_pass")
        if st.button("Sign up"):
            ok, msg = register_user(new_username, new_password)
            st.success(msg) if ok else st.error(msg)


def main_app():
    similarity = load_similarity()
    titles = get_all_titles()
    user_id = st.session_state.user_id

    # --- Sidebar: account, favorites, history ---
    st.sidebar.write(f"Logged in as **{st.session_state.username}**")
    if st.sidebar.button("Log out"):
        st.session_state.pop("user_id", None)
        st.session_state.pop("username", None)
        st.rerun()

    st.sidebar.subheader("⭐ Your Favorites")
    favs = get_favorites(user_id)
    if favs:
        for _row_id, title in favs:
            st.sidebar.write(f"- {title}")
    else:
        st.sidebar.caption("No favorites yet — add some below!")

    st.sidebar.subheader("🕘 Recent Searches")
    hist = get_history(user_id, limit=5)
    if hist:
        for title, _recs, ts in hist:
            st.sidebar.caption(f"{ts:%Y-%m-%d %H:%M} — {title}")
    else:
        st.sidebar.caption("No history yet.")

    # --- Main panel ---
    st.header("Movie Recommender System")
    selected_movie = st.selectbox("Type or select a movie from the dropdown", titles)

    if st.button("Show Recommendation"):
        names, posters, row_ids = recommend(selected_movie, similarity)
        if not names:
            st.warning("No recommendations found for that title.")
            st.session_state.pop("last_recs", None)
        else:
            searched_movie = get_movie_by_title(selected_movie)
            log_history(user_id, searched_movie.id, names)
            # Persist results so they survive the rerun triggered by a
            # favorite-button click below (that click is a separate rerun
            # in which "Show Recommendation" itself is no longer True).
            st.session_state.last_recs = {
                "names": names,
                "posters": posters,
                "row_ids": row_ids,
            }

    # Render the most recent recommendations (if any) from session_state,
    # independent of whether "Show Recommendation" was clicked on *this* run.
    if "last_recs" in st.session_state:
        names = st.session_state.last_recs["names"]
        posters = st.session_state.last_recs["posters"]
        row_ids = st.session_state.last_recs["row_ids"]

        cols = st.columns(5)
        for col, name, poster, row_id in zip(cols, names, posters, row_ids):
            with col:
                st.text(name)
                st.image(poster)
                already_fav = is_favorite(user_id, row_id)
                label = "💔 Remove favorite" if already_fav else "❤️ Add favorite"
                if st.button(label, key=f"fav_{row_id}"):
                    if already_fav:
                        remove_favorite(user_id, row_id)
                    else:
                        add_favorite(user_id, row_id)
                    st.rerun()


def main():
    init_db()
    if "user_id" not in st.session_state:
        login_screen()
    else:
        main_app()


if __name__ == "__main__":
    main()
