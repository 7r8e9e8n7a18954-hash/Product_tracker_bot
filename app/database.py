import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

class Database:
    def __init__(self, path: str):
        self.path = path
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    shop TEXT NOT NULL DEFAULT 'unknown',
                    title TEXT NOT NULL DEFAULT 'Unverified product link',
                    last_price REAL,
                    currency TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, url)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_user ON products(user_id)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT,
                    checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_id, checked_at)")

    def add_product(self, user_id: int, url: str, max_links: int) -> tuple[bool, int | None]:
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM products WHERE user_id=? AND url=?", (user_id, url)
            ).fetchone()
            if existing:
                return False, int(existing["id"])
            count = conn.execute("SELECT COUNT(*) AS n FROM products WHERE user_id=?", (user_id,)).fetchone()["n"]
            if count >= max_links:
                return False, None
            cur = conn.execute("INSERT INTO products(user_id, url) VALUES(?, ?)", (user_id, url))
            return True, int(cur.lastrowid)

    def list_products(self, user_id: int):
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, url, shop, title, last_price, currency, created_at FROM products WHERE user_id=? ORDER BY id DESC",
                (user_id,),
            ).fetchall()

    def get_product(self, user_id: int, product_id: int):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM products WHERE user_id=? AND id=?", (user_id, product_id)
            ).fetchone()

    def delete_product(self, user_id: int, product_id: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM products WHERE user_id=? AND id=?", (user_id, product_id))
            return cur.rowcount > 0

    def list_all_products(self):
        """Return tracked products for background checks."""
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, user_id, url, shop, title, last_price, currency FROM products ORDER BY id"
            ).fetchall()

    def save_price(self, product_id: int, price: float, currency: str, title: str, shop: str) -> float | None:
        """Save a verified price and history row; return the previous price, if any."""
        with self.connect() as conn:
            row = conn.execute("SELECT last_price FROM products WHERE id=?", (product_id,)).fetchone()
            if row is None:
                return None
            previous = row["last_price"]
            conn.execute(
                "UPDATE products SET last_price=?, currency=?, title=?, shop=? WHERE id=?",
                (price, currency, title, shop, product_id),
            )
            conn.execute(
                "INSERT INTO price_history(product_id, price, currency) VALUES(?, ?, ?)",
                (product_id, price, currency),
            )
            return float(previous) if previous is not None else None

    def get_price_history(self, user_id: int, product_id: int, limit: int = 10):
        with self.connect() as conn:
            owned = conn.execute(
                "SELECT id FROM products WHERE user_id=? AND id=?", (user_id, product_id)
            ).fetchone()
            if not owned:
                return []
            return conn.execute(
                "SELECT price, currency, checked_at FROM price_history WHERE product_id=? ORDER BY id DESC LIMIT ?",
                (product_id, max(1, min(int(limit), 50))),
            ).fetchall()
