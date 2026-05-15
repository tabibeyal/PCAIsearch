import sqlite3
from pathlib import Path

import pytest

from analysis.parallels.schema import open_db, create_tables
from analysis.parallels.detector import build_parallels
from analysis.parallels.queries import (
    list_spans,
    show_span,
    spans_in_sutta,
    top_formulas,
    stats,
)

SUTTA_A = {
    "sutta_id": "MN 1",
    "verses": [
        {"number": 1, "pali": "evaṃ me sutaṃ ekaṃ samayaṃ"},
        {"number": 2, "pali": "viharati jhānaṃ upasampajja"},
    ],
}

SUTTA_B = {
    "sutta_id": "MN 2",
    "verses": [
        {"number": 1, "pali": "evaṃ me sutaṃ ekaṃ samayaṃ"},
        {"number": 2, "pali": "viharati jhānaṃ upasampajja"},
    ],
}


@pytest.fixture()
def populated_db(tmp_path):
    conn = open_db(tmp_path / "p.sqlite")
    create_tables(conn)
    build_parallels([SUTTA_A, SUTTA_B], conn, k=4)
    return conn


def test_list_spans_returns_list(populated_db):
    rows = list_spans(populated_db)
    assert isinstance(rows, list)
    assert len(rows) >= 1


def test_list_spans_min_occurrences_filter(populated_db):
    rows_all = list_spans(populated_db, min_occurrences=1)
    rows_high = list_spans(populated_db, min_occurrences=999)
    assert len(rows_high) == 0
    assert len(rows_all) >= 1


def test_list_spans_limit(populated_db):
    rows = list_spans(populated_db, limit=1)
    assert len(rows) <= 1


def test_show_span_found(populated_db):
    span_id = list_spans(populated_db, limit=1)[0]["id"]
    result = show_span(populated_db, span_id)
    assert result is not None
    assert result["span"]["id"] == span_id
    assert isinstance(result["occurrences"], list)


def test_show_span_not_found(populated_db):
    assert show_span(populated_db, "000000000000") is None


def test_spans_in_sutta(populated_db):
    rows = spans_in_sutta(populated_db, "MN 1")
    assert len(rows) >= 1


def test_spans_in_sutta_unknown(populated_db):
    rows = spans_in_sutta(populated_db, "XY 99")
    assert rows == []


def test_top_formulas_by_occurrences(populated_db):
    rows = top_formulas(populated_db, by="occurrences", limit=5)
    assert len(rows) >= 1


def test_top_formulas_by_tokens(populated_db):
    rows = top_formulas(populated_db, by="tokens", limit=5)
    assert len(rows) >= 1


def test_stats_keys(populated_db):
    result = stats(populated_db)
    assert "total_spans" in result
    assert "total_occurrences" in result
    assert "detector_version" in result
