import json

from backend.app.services.passage_context import PassageStore


def _store(tmp_path, sutta_id, englishes):
    verses = [{"number": i, "pali": "", "english": e} for i, e in enumerate(englishes, start=1)]
    (tmp_path / f"{sutta_id}.json").write_text(
        json.dumps({"sutta_id": sutta_id, "verses": verses}), encoding="utf-8"
    )
    return PassageStore.from_directory(tmp_path)


def test_short_verse_includes_surrounding_neighbors(tmp_path):
    store = _store(tmp_path, "SN35.20", ["header", "title", "a" * 150, "b" * 150, "c" * 150, "d" * 150])
    result = store.passage("SN 35.20:4")
    assert [line["isMatch"] for line in result] == [False, True, False]


def test_long_verse_stands_alone(tmp_path):
    store = _store(tmp_path, "MN1", ["header", "title", "x" * 200])
    assert store.passage("MN 1:3") is None


def test_header_and_title_are_not_neighbors(tmp_path):
    store = _store(tmp_path, "SN1.1", ["header", "title", "a" * 150, "b" * 150])
    result = store.passage("SN 1.1:3")
    assert {line["id"] for line in result} == {"SN 1.1:3", "SN 1.1:4"}
