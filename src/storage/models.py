import sqlite3
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent
DB_PATH = _ROOT / "trend_catcher.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS category_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(category_id, keyword),
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            published TEXT,
            source TEXT,
            snippet TEXT,
            category_id INTEGER NOT NULL,
            keyword TEXT,
            fetched_at TEXT NOT NULL,
            url_hash TEXT UNIQUE,
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_news_category ON news_items(category_id);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_news_fetched ON news_items(fetched_at);"
    )
    conn.commit()

    existing = {
        row[0]
        for row in conn.execute("SELECT name FROM categories;").fetchall()
        if row and row[0]
    }
    defaults = ["舆情监测", "媒体传播"]
    for name in defaults:
        if name not in existing:
            conn.execute("INSERT INTO categories (name) VALUES (?);", (name,))
    conn.commit()


def save_news_items(conn: sqlite3.Connection, items: list[dict]) -> int:
    import hashlib

    count = 0
    for item in items:
        url_hash = hashlib.md5(item["url"].encode()).hexdigest()
        try:
            conn.execute(
                """
                INSERT INTO news_items
                (title, url, published, source, snippet, category_id, keyword, fetched_at, url_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    item["title"],
                    item["url"],
                    item.get("published", ""),
                    item.get("source", ""),
                    item.get("snippet", ""),
                    item["category_id"],
                    item.get("keyword", ""),
                    item["fetched_at"],
                    url_hash,
                ),
            )
            count += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return count


def list_news_items(
    conn: sqlite3.Connection,
    category_id: int,
    limit: int = 200,
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, title, url, published, source, snippet, fetched_at
        FROM news_items
        WHERE category_id = ?
        ORDER BY fetched_at DESC
        LIMIT ?;
        """,
        (category_id, limit),
    ).fetchall()


def clear_news_items(conn: sqlite3.Connection, category_id: int) -> None:
    conn.execute("DELETE FROM news_items WHERE category_id = ?;", (category_id,))
    conn.commit()


def list_categories(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    rows = conn.execute("SELECT id, name FROM categories ORDER BY id ASC;").fetchall()
    return [(int(r[0]), str(r[1])) for r in rows]


def create_category(conn: sqlite3.Connection, name: str) -> int:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("分类名不能为空")
    cur = conn.execute("INSERT INTO categories (name) VALUES (?);", (cleaned,))
    conn.commit()
    return int(cur.lastrowid)


def delete_category(conn: sqlite3.Connection, category_id: int) -> None:
    conn.execute("DELETE FROM categories WHERE id = ?;", (category_id,))
    conn.commit()


def list_keywords(conn: sqlite3.Connection, category_id: int) -> list[tuple[int, str]]:
    rows = conn.execute(
        "SELECT id, keyword FROM category_keywords WHERE category_id = ? ORDER BY id ASC;",
        (category_id,),
    ).fetchall()
    return [(int(r[0]), str(r[1])) for r in rows]


def add_keyword(conn: sqlite3.Connection, category_id: int, keyword: str) -> None:
    cleaned = keyword.strip()
    if not cleaned:
        raise ValueError("关键词不能为空")
    conn.execute(
        "INSERT OR IGNORE INTO category_keywords (category_id, keyword) VALUES (?, ?);",
        (category_id, cleaned),
    )
    conn.commit()


def delete_keyword(conn: sqlite3.Connection, keyword_id: int) -> None:
    conn.execute("DELETE FROM category_keywords WHERE id = ?;", (keyword_id,))
    conn.commit()


def first_category_id(categories: list[tuple[int, str]]) -> int | None:
    return categories[0][0] if categories else None