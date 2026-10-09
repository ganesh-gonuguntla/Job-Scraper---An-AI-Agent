import hashlib
import json
import sqlite3
from typing import Tuple
from backend.config import CACHE_DB_PATH
from backend.schemas import Profile, SearchQuery, Job, Score

def get_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

class SQLiteCache:
    def __init__(self, db_path: str = str(CACHE_DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_profiles (
                    resume_hash TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    queries_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_jobs (
                    url_hash TEXT PRIMARY KEY,
                    job_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_scores (
                    resume_hash TEXT NOT NULL,
                    url_hash TEXT NOT NULL,
                    score_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (resume_hash, url_hash)
                )
            """)
            conn.commit()

    def get_profile_and_queries(self, resume_hash: str) -> Tuple[Profile, list[SearchQuery]] | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT profile_json, queries_json FROM cache_profiles WHERE resume_hash = ?",
                (resume_hash,)
            )
            row = cursor.fetchone()
            if row:
                profile_data = json.loads(row["profile_json"])
                queries_data = json.loads(row["queries_json"])
                profile = Profile.model_validate(profile_data)
                queries = [SearchQuery.model_validate(q) for q in queries_data]
                return profile, queries
        return None

    def set_profile_and_queries(self, resume_hash: str, profile: Profile, queries: list[SearchQuery]) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache_profiles (resume_hash, profile_json, queries_json)
                VALUES (?, ?, ?)
                """,
                (
                    resume_hash,
                    profile.model_dump_json(),
                    json.dumps([q.model_dump() for q in queries])
                )
            )
            conn.commit()

    def get_job(self, url: str) -> Job | None:
        url_hash = get_hash(url)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT job_json FROM cache_jobs WHERE url_hash = ?",
                (url_hash,)
            )
            row = cursor.fetchone()
            if row:
                return Job.model_validate_json(row["job_json"])
        return None

    def set_job(self, url: str, job: Job) -> None:
        url_hash = get_hash(url)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache_jobs (url_hash, job_json)
                VALUES (?, ?)
                """,
                (url_hash, job.model_dump_json())
            )
            conn.commit()

    def get_score(self, resume_hash: str, url: str) -> Score | None:
        url_hash = get_hash(url)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT score_json FROM cache_scores WHERE resume_hash = ? AND url_hash = ?",
                (resume_hash, url_hash)
            )
            row = cursor.fetchone()
            if row:
                return Score.model_validate_json(row["score_json"])
        return None

    def set_score(self, resume_hash: str, url: str, score: Score) -> None:
        url_hash = get_hash(url)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache_scores (resume_hash, url_hash, score_json)
                VALUES (?, ?, ?)
                """,
                (resume_hash, url_hash, score.model_dump_json())
            )
            conn.commit()

cache = SQLiteCache()
