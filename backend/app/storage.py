from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schemas import ReviewResponse, ReviewHistoryItem

DB_PATH = Path("review_assistant.db")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                repo_url TEXT,
                branch TEXT,
                payload_json TEXT NOT NULL,
                summary TEXT NOT NULL,
                comment_count INTEGER NOT NULL,
                high_count INTEGER NOT NULL,
                medium_count INTEGER NOT NULL,
                low_count INTEGER NOT NULL,
                info_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(email: str, password: str) -> dict:
    token = secrets.token_urlsafe(32)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users(email, password_hash, token, created_at) VALUES (?, ?, ?, ?)",
            (email.lower().strip(), hash_password(password), token, now_iso()),
        )
        row = conn.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
    return dict(row)


def authenticate(email: str, password: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password_hash = ?",
            (email.lower().strip(), hash_password(password)),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_token(token: str | None) -> Optional[dict]:
    if not token:
        return None
    token = token.replace("Bearer ", "").strip()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
    return dict(row) if row else None


def save_review(user_id: int | None, title: str, repo_url: str | None, branch: str | None, response: ReviewResponse) -> int:
    counts = {
        "high": sum(1 for c in response.comments if c.severity == "high"),
        "medium": sum(1 for c in response.comments if c.severity == "medium"),
        "low": sum(1 for c in response.comments if c.severity == "low"),
        "info": sum(1 for c in response.comments if c.severity == "info"),
    }
    payload = response.model_dump(mode="json")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO reviews(user_id, title, repo_url, branch, payload_json, summary, comment_count,
              high_count, medium_count, low_count, info_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                title,
                repo_url,
                branch,
                json.dumps(payload),
                response.summary,
                len(response.comments),
                counts["high"],
                counts["medium"],
                counts["low"],
                counts["info"],
                now_iso(),
            ),
        )
        review_id = int(cur.lastrowid)
    return review_id


def list_reviews(user_id: int | None = None) -> list[ReviewHistoryItem]:
    query = "SELECT * FROM reviews"
    params: tuple = ()
    if user_id is not None:
        query += " WHERE user_id = ?"
        params = (user_id,)
    query += " ORDER BY id DESC LIMIT 30"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        ReviewHistoryItem(
            id=row["id"],
            title=row["title"],
            repo_url=row["repo_url"],
            branch=row["branch"],
            summary=row["summary"],
            created_at=row["created_at"],
            comment_count=row["comment_count"],
            high_count=row["high_count"],
            medium_count=row["medium_count"],
            low_count=row["low_count"],
            info_count=row["info_count"],
        ) for row in rows
    ]


def get_review(review_id: int, user_id: int | None = None) -> Optional[ReviewResponse]:
    query = "SELECT * FROM reviews WHERE id = ?"
    params: tuple = (review_id,)
    if user_id is not None:
        query += " AND user_id = ?"
        params = (review_id, user_id)
    with get_conn() as conn:
        row = conn.execute(query, params).fetchone()
    if not row:
        return None
    data = json.loads(row["payload_json"])
    data["id"] = row["id"]
    return ReviewResponse(**data)
