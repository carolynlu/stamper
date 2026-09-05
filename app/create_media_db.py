import os
import sqlite3
from dotenv import load_dotenv

from app.tmdb import main as fetch_tmdb, fetch_featured, parse_tmdb_items
from app.anilist import main as fetch_anilist, fetch_anime, parse_anime

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "media.db")


def create_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS media (
            tmdb_id INTEGER PRIMARY KEY,
            title TEXT,
            media_type TEXT,
            poster_url TEXT,
            overview TEXT,
            release_date TEXT,
            runtime INTEGER,
            vote_average REAL
        );

        CREATE TABLE IF NOT EXISTS featured_movies (
            tmdb_id INTEGER PRIMARY KEY,
            title TEXT,
            media_type TEXT,
            poster_url TEXT,
            overview TEXT,
            release_date TEXT,
            runtime INTEGER,
            vote_average REAL,
            rank INTEGER
        );

        CREATE TABLE IF NOT EXISTS featured_tv (
            tmdb_id INTEGER PRIMARY KEY,
            title TEXT,
            media_type TEXT,
            poster_url TEXT,
            overview TEXT,
            release_date TEXT,
            runtime INTEGER,
            vote_average REAL,
            rank INTEGER
        );

        CREATE TABLE IF NOT EXISTS seasons (
            season_id TEXT PRIMARY KEY,
            tv_id INTEGER,
            title TEXT,
            season_number INTEGER,
            name TEXT,
            overview TEXT,
            poster_url TEXT,
            air_date TEXT,
            episode_count INTEGER,
            vote_average REAL
        );

        CREATE TABLE IF NOT EXISTS episodes (
            episode_id INTEGER PRIMARY KEY,
            season_id TEXT,
            tv_id INTEGER,
            season_number INTEGER,
            episode_number INTEGER,
            episode_name TEXT,
            overview TEXT,
            air_date TEXT,
            runtime INTEGER,
            vote_average REAL,
            still_url TEXT
        );

        CREATE TABLE IF NOT EXISTS anime (
            anilist_id INTEGER PRIMARY KEY,
            title_romaji TEXT,
            title_english TEXT,
            episodes INTEGER,
            average_score TEXT,
            trending INTEGER,
            genres TEXT,
            description TEXT,
            cover_url TEXT,
            start_date TEXT
        );

        CREATE TABLE IF NOT EXISTS anime_ep (
            episode_id INTEGER PRIMARY KEY,
            anilist_id INTEGER,
            episode_title TEXT,
            thumbnail TEXT,
            duration INTEGER
        );
    """)
    conn.commit()


def insert_media(conn, items):
    conn.executemany(
        """INSERT OR REPLACE INTO media
           (tmdb_id, title, media_type, poster_url, overview, release_date, runtime, vote_average)
           VALUES (:tmdb_id, :title, :media_type, :poster_url, :overview, :release_date, :runtime, :vote_average)""",
        items,
    )


def insert_featured(conn, table, items):
    conn.executemany(
        f"""INSERT OR REPLACE INTO {table}
           (tmdb_id, title, media_type, poster_url, overview, release_date, runtime, vote_average, rank)
           VALUES (:tmdb_id, :title, :media_type, :poster_url, :overview, :release_date, :runtime, :vote_average, :rank)""",
        items,
    )


def insert_seasons(conn, seasons):
    conn.executemany(
        """INSERT OR REPLACE INTO seasons
           (season_id, tv_id, title, season_number, name, overview, poster_url, air_date, episode_count, vote_average)
           VALUES (:season_id, :tv_id, :title, :season_number, :name, :overview, :poster_url, :air_date, :episode_count, :vote_average)""",
        seasons,
    )


def insert_episodes(conn, episodes):
    conn.executemany(
        """INSERT OR REPLACE INTO episodes
           (episode_id, season_id, tv_id, season_number, episode_number, episode_name, overview, air_date, runtime, vote_average, still_url)
           VALUES (:episode_id, :season_id, :tv_id, :season_number, :episode_number, :episode_name, :overview, :air_date, :runtime, :vote_average, :still_url)""",
        episodes,
    )


def insert_anime(conn, anime):
    conn.executemany(
        """INSERT OR REPLACE INTO anime
           (anilist_id, title_romaji, title_english, episodes, average_score, trending, genres, description, cover_url, start_date)
           VALUES (:anilist_id, :title_romaji, :title_english, :episodes, :average_score, :trending, :genres, :description, :cover_url, :start_date)""",
        anime,
    )


def insert_anime_episodes(conn, episodes):
    conn.executemany(
        """INSERT OR REPLACE INTO anime_ep
           (episode_id, anilist_id, episode_title, thumbnail, duration)
           VALUES (:episode_id, :anilist_id, :episode_title, :thumbnail, :duration)""",
        episodes,
    )


def seed_catalogue(db_path):
    """Lightweight seed (~5 API calls) — fetches only what the catalogue page needs.

    Episodes and runtimes are deferred to on-demand cache (cache_tmdb.py).
    Safe to call repeatedly; all inserts use INSERT OR REPLACE.
    Each section is wrapped so one API failure doesn't prevent the app from starting.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    create_tables(conn)

    try:
        print("[seed_catalogue] Fetching featured movies...")
        raw_movies = fetch_featured("movie", pages=2)
        featured_movies = parse_tmdb_items(raw_movies, "movie", include_rank=True, include_runtime=False)
        insert_featured(conn, "featured_movies", featured_movies)
        conn.commit()
        print(f"[seed_catalogue] {len(featured_movies)} movies seeded.")
    except Exception as e:
        print(f"[seed_catalogue] WARNING: failed to seed movies: {e}")

    try:
        print("[seed_catalogue] Fetching featured TV shows...")
        raw_tv = fetch_featured("tv", pages=2)
        featured_tv = parse_tmdb_items(raw_tv, "tv", include_rank=True, include_runtime=False)
        insert_featured(conn, "featured_tv", featured_tv)
        conn.commit()
        print(f"[seed_catalogue] {len(featured_tv)} TV shows seeded.")
    except Exception as e:
        print(f"[seed_catalogue] WARNING: failed to seed TV shows: {e}")

    try:
        print("[seed_catalogue] Fetching anime...")
        anime_data = parse_anime(fetch_anime(pages=1))
        insert_anime(conn, anime_data)
        conn.commit()
        print(f"[seed_catalogue] {len(anime_data)} anime seeded.")
    except Exception as e:
        print(f"[seed_catalogue] WARNING: failed to seed anime: {e}")

    conn.close()
    print("[seed_catalogue] Done.")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)

    print("Fetching TMDB data...")
    featured_movies, featured_tv, popular_movies, popular_tv, seasons, episodes = fetch_tmdb()
    insert_featured(conn, "featured_movies", featured_movies)
    insert_featured(conn, "featured_tv", featured_tv)
    insert_media(conn, popular_movies)
    insert_media(conn, popular_tv)
    insert_seasons(conn, seasons)
    insert_episodes(conn, episodes)
    conn.commit()
    print(f"  {len(featured_movies)} featured movies, {len(featured_tv)} featured TV shows")
    print(f"  {len(popular_movies)} popular movies, {len(popular_tv)} popular TV shows")
    print(f"  {len(seasons)} seasons, {len(episodes)} episodes")

    print("Fetching AniList data...")
    anime, anime_eps = fetch_anilist()
    insert_anime(conn, anime)
    insert_anime_episodes(conn, anime_eps)
    conn.commit()
    print(f"  {len(anime)} anime, {len(anime_eps)} anime episodes")

    conn.close()
    print("media.db built successfully.")
