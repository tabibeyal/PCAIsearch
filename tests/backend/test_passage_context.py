import json

from backend.app.services.passage_context import PassageStore


def _store(tmp_path, sutta_id, englishes, sections=None):
    verses = []
    for i, e in enumerate(englishes, start=1):
        v = {"number": i, "english": e}
        if sections and sections[i - 1] is not None:
            v["section"] = sections[i - 1]
        verses.append(v)
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


# ── Canon/commentary boundary (#103) ───────────────────────────────────────────
# Layout: verses 3–4 commentary, 5–6 canon. Verse 4 and verse 5 sit on either
# side of the boundary, so each anchor's window can only widen into its own
# section without crossing.

_BOUNDARY_SECTIONS = [None, None, "commentary", "commentary", None, None]


def test_canon_verse_at_boundary_widens_only_into_canon(tmp_path):
    store = _store(
        tmp_path,
        "MN99",
        ["header", "title", "c" * 150, "d" * 150, "e" * 150, "f" * 150],
        _BOUNDARY_SECTIONS,
    )
    result = store.passage("MN 99:5")
    assert {line["id"] for line in result} == {"MN 99:5", "MN 99:6"}


def test_commentary_verse_at_boundary_widens_only_into_commentary(tmp_path):
    store = _store(
        tmp_path,
        "MN99",
        ["header", "title", "c" * 150, "d" * 150, "e" * 150, "f" * 150],
        _BOUNDARY_SECTIONS,
    )
    result = store.passage("MN 99:4")
    assert {line["id"] for line in result} == {"MN 99:3", "MN 99:4"}
