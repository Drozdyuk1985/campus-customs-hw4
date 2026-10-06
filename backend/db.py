"""Database paths and connections shared by the backend modules."""

import sqlite3
from pathlib import Path

HW4_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = HW4_DIR / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
PRODUCTS_DIR = DATA_DIR / "products"


def connect_ro() -> sqlite3.Connection:
    """Read-only connection: used by routes that only look things up."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def connect_rw() -> sqlite3.Connection:
    """Read-write connection: used only for accounts and login sessions."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
