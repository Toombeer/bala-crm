"""Доступ к базе данных и миграции.

Сейчас используется SQLite (WAL). Весь SQL написан в переносимом виде и собран здесь
и в сервисах, чтобы переход на PostgreSQL сводился к замене этого модуля.
"""
import json
import os
import sqlite3
from contextlib import contextmanager

from .config import settings

MIGRATIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrations')


def connect(path: str | None = None) -> sqlite3.Connection:
    path = path or settings.db_path
    if path != ':memory:' and os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA busy_timeout = 15000')
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    done = {r['name'] for r in conn.execute('SELECT name FROM schema_migrations')}
    applied = []
    for name in sorted(f for f in os.listdir(MIGRATIONS) if f.endswith('.sql')):
        if name in done:
            continue
        with open(os.path.join(MIGRATIONS, name), encoding='utf-8') as f:
            sql = f.read()
        conn.execute('BEGIN')
        try:
            for stmt in [s for s in sql.split(';\n') if s.strip()]:
                conn.execute(stmt)
            conn.execute('INSERT INTO schema_migrations (name) VALUES (?)', (name,))
            conn.execute('COMMIT')
        except Exception:
            conn.execute('ROLLBACK')
            raise
        applied.append(name)
    return applied


@contextmanager
def tx(conn: sqlite3.Connection):
    """Транзакция: всё или ничего."""
    conn.execute('BEGIN IMMEDIATE')
    try:
        yield conn
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise


def row(r: sqlite3.Row | None) -> dict | None:
    return dict(r) if r is not None else None


def rows(rs) -> list[dict]:
    return [dict(r) for r in rs]


def jload(s, default):
    try:
        return json.loads(s) if s else default
    except (TypeError, ValueError):
        return default
