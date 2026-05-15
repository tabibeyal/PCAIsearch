import sqlite3
import tempfile
from pathlib import Path

import pytest

from analysis.parallels.schema import open_db, create_tables
from analysis.parallels.detector import build_parallels


# Minimal sutta fixture: a formula repeated across two suttas
SUTTA_A = {
    "sutta_id": "MN 1",
    "verses": [
        {"number": 1, "pali": "evaṃ me sutaṃ ekaṃ samayaṃ"},
        {"number": 2, "pali": "viharati jhānaṃ upasampajja"},
        {"number": 3, "pali": "viharati jhānaṃ upasampajja"},  # intra-sutta repeat
    ],
}

SUTTA_B = {
    "sutta_id": "MN 2",
    "verses": [
        {"number": 1, "pali": "evaṃ me sutaṃ ekaṃ samayaṃ"},
        {"number": 2, "pali": "viharati jhānaṃ upasampajja"},
    ],
}

SUTTA_UNIQUE = {
    "sutta_id": "MN 3",
    "verses": [
        {"number": 1, "pali": "idaṃ vuttaṃ bhagavatā"},
    ],
}


@pytest.fixture()
def db_path(tmp_path):
    p = tmp_path / "parallels.sqlite"
    return p


def test_schema_creates_tables(db_path):
    conn = open_db(db_path)
    create_tables(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "span" in tables
    assert "occurrence" in tables
    conn.close()


def test_build_finds_cross_sutta_span(db_path):
    conn = open_db(db_path)
    create_tables(conn)
    build_parallels([SUTTA_A, SUTTA_B], conn, k=4)
    # "evaṃ me sutaṃ ekaṃ samayaṃ" is 5 tokens -> maximal span across both suttas
    spans = conn.execute("SELECT * FROM span").fetchall()
    assert len(spans) >= 1
    conn.close()


def test_build_cross_sutta_occurrence_count(db_path):
    conn = open_db(db_path)
    create_tables(conn)
    build_parallels([SUTTA_A, SUTTA_B], conn, k=4)
    rows = conn.execute(
        "SELECT occurrence_count FROM span ORDER BY occurrence_count DESC LIMIT 1"
    ).fetchone()
    assert rows is not None
    # "evaṃ me sutaṃ ekaṃ samayaṃ" appears in MN1:v1 and MN2:v1 (+MN1:v1 intra if detected)
    assert rows[0] >= 2
    conn.close()


def test_build_no_span_for_unique_text(db_path):
    conn = open_db(db_path)
    create_tables(conn)
    build_parallels([SUTTA_UNIQUE], conn, k=4)
    spans = conn.execute("SELECT * FROM span").fetchall()
    assert len(spans) == 0
    conn.close()


def test_span_id_content_addressed(db_path):
    conn = open_db(db_path)
    create_tables(conn)
    build_parallels([SUTTA_A, SUTTA_B], conn, k=4)
    span_id = conn.execute("SELECT id FROM span LIMIT 1").fetchone()[0]
    # span IDs are 12-char hex strings
    assert len(span_id) == 12
    assert all(c in "0123456789abcdef" for c in span_id)
    conn.close()


def test_span_detector_version(db_path):
    conn = open_db(db_path)
    create_tables(conn)
    build_parallels([SUTTA_A, SUTTA_B], conn, k=4)
    version = conn.execute("SELECT detector_version FROM span LIMIT 1").fetchone()[0]
    assert version == "v1-k7-light"
    conn.close()


def test_build_idempotent(db_path):
    conn = open_db(db_path)
    create_tables(conn)
    build_parallels([SUTTA_A, SUTTA_B], conn, k=4)
    count_first = conn.execute("SELECT COUNT(*) FROM span").fetchone()[0]
    build_parallels([SUTTA_A, SUTTA_B], conn, k=4)
    count_second = conn.execute("SELECT COUNT(*) FROM span").fetchone()[0]
    assert count_first == count_second
    conn.close()
