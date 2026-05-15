import sqlite3
from pathlib import Path


def open_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS span (
            id               TEXT PRIMARY KEY,
            normalised_pali  TEXT NOT NULL,
            token_count      INTEGER NOT NULL,
            occurrence_count INTEGER NOT NULL DEFAULT 0,
            detector_version TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS occurrence (
            id          INTEGER PRIMARY KEY,
            span_id     TEXT NOT NULL REFERENCES span(id),
            sutta_id    TEXT NOT NULL,
            verse_number INTEGER NOT NULL,
            char_offset  INTEGER NOT NULL,
            char_length  INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS occ_span ON occurrence(span_id);
        CREATE INDEX IF NOT EXISTS occ_sutta ON occurrence(sutta_id);
    """)
    conn.commit()
