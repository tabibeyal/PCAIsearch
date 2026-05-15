import argparse
import json
import sys
from pathlib import Path

from analysis.parallels.schema import open_db, create_tables
from analysis.parallels import queries as Q

DEFAULT_DB = Path("data/parallels.sqlite")
DEFAULT_DUMPS = Path("data/dumps")


def _print(data, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(data)


def cmd_build(args):
    import json as _json
    from analysis.parallels.detector import build_parallels

    dumps_dir = Path(args.dumps)
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = open_db(db_path)
    create_tables(conn)

    paths = sorted(dumps_dir.glob("*.json"))
    if not paths:
        print(f"No JSON files in {dumps_dir}", file=sys.stderr)
        sys.exit(1)

    suttas = []
    for p in paths:
        try:
            suttas.append(_json.loads(p.read_text()))
        except Exception as e:
            print(f"Warning: skipping {p.name}: {e}", file=sys.stderr)

    print(f"Building parallels from {len(suttas)} suttas…", file=sys.stderr)
    build_parallels(suttas, conn)
    s = Q.stats(conn)
    print(f"Done. {s['total_spans']} spans, {s['total_occurrences']} occurrences ({s['detector_version']})")
    conn.close()


def cmd_list_spans(args):
    conn = open_db(Path(args.db))
    rows = Q.list_spans(conn, min_occurrences=args.min_occurrences, min_tokens=args.min_tokens, limit=args.limit)
    if args.json:
        _print(rows, True)
    else:
        for r in rows:
            print(f"{r['id']}  occ={r['occurrence_count']}  tok={r['token_count']}  {r['normalised_pali'][:60]}")
    conn.close()


def cmd_show_span(args):
    conn = open_db(Path(args.db))
    result = Q.show_span(conn, args.span_id)
    if result is None:
        print(f"Span {args.span_id!r} not found.", file=sys.stderr)
        sys.exit(1)
    if args.json:
        _print(result, True)
    else:
        s = result["span"]
        print(f"ID:      {s['id']}")
        print(f"Tokens:  {s['token_count']}")
        print(f"Occurrences: {s['occurrence_count']}")
        print(f"Version: {s['detector_version']}")
        print(f"Text:    {s['normalised_pali']}")
        print()
        for o in result["occurrences"]:
            print(f"  {o['sutta_id']} v{o['verse_number']} @{o['char_offset']}+{o['char_length']}")
    conn.close()


def cmd_spans_in_sutta(args):
    conn = open_db(Path(args.db))
    rows = Q.spans_in_sutta(conn, args.sutta_id, min_tokens=args.min_tokens)
    if args.json:
        _print(rows, True)
    else:
        for r in rows:
            print(f"{r['id']}  occ={r['occurrence_count']}  tok={r['token_count']}  {r['normalised_pali'][:60]}")
    conn.close()


def cmd_top_formulas(args):
    conn = open_db(Path(args.db))
    rows = Q.top_formulas(conn, by=args.by, limit=args.limit)
    if args.json:
        _print(rows, True)
    else:
        for r in rows:
            print(f"{r['id']}  occ={r['occurrence_count']}  tok={r['token_count']}  {r['normalised_pali'][:60]}")
    conn.close()


def cmd_stats(args):
    conn = open_db(Path(args.db))
    s = Q.stats(conn)
    if args.json:
        _print(s, True)
    else:
        print(f"Spans:       {s['total_spans']}")
        print(f"Occurrences: {s['total_occurrences']}")
        print(f"Version:     {s['detector_version']}")
    conn.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m analysis.parallels",
        description="Pāḷi parallel-passage detector",
    )
    p.add_argument("--db", default=str(DEFAULT_DB), help="SQLite artifact path")

    sub = p.add_subparsers(dest="command", required=True)

    bp = sub.add_parser("build", help="Rebuild parallels.sqlite from data/dumps/*.json")
    bp.add_argument("--dumps", default=str(DEFAULT_DUMPS))
    bp.set_defaults(func=cmd_build)

    lp = sub.add_parser("list-spans", help="List spans ranked by occurrence count")
    lp.add_argument("--min-occurrences", type=int, default=2)
    lp.add_argument("--min-tokens", type=int, default=1)
    lp.add_argument("--limit", type=int, default=50)
    lp.add_argument("--json", action="store_true")
    lp.set_defaults(func=cmd_list_spans)

    sp = sub.add_parser("show-span", help="Show one span with all occurrences")
    sp.add_argument("span_id")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_show_span)

    sip = sub.add_parser("spans-in-sutta", help="Spans appearing in a specific sutta")
    sip.add_argument("sutta_id")
    sip.add_argument("--min-tokens", type=int, default=1)
    sip.add_argument("--json", action="store_true")
    sip.set_defaults(func=cmd_spans_in_sutta)

    tf = sub.add_parser("top-formulas", help="Highest-recurrence or longest spans")
    tf.add_argument("--by", choices=["occurrences", "tokens"], default="occurrences")
    tf.add_argument("--limit", type=int, default=20)
    tf.add_argument("--json", action="store_true")
    tf.set_defaults(func=cmd_top_formulas)

    st = sub.add_parser("stats", help="Summary statistics for the artifact")
    st.add_argument("--json", action="store_true")
    st.set_defaults(func=cmd_stats)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
