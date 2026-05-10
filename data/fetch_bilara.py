"""
Downloads DN, MN, AN, SN and selected KN texts from bilara-data (sparse checkout)
and converts to the format expected by process_dumps.py:
  { "sutta_id": "AN1.1", "verses": [{"number": 1, "pali": "...", "english": "..."}, ...] }
"""
import json
import subprocess
from pathlib import Path

REPO_URL = "https://github.com/suttacentral/bilara-data.git"
CLONE_DIR = Path("/tmp/bilara-data")
DUMP_DIR = Path(__file__).parent / "dumps"

COLLECTIONS = ["dn", "mn", "an", "sn"]
KN_COLLECTIONS = ["kn/dhp", "kn/iti"]

PALI_PREFIX = "root/pli/ms/sutta"
EN_PREFIX = "translation/en/sujato/sutta"


def sparse_clone():
    paths = []
    for col in COLLECTIONS + KN_COLLECTIONS:
        paths += [f"{PALI_PREFIX}/{col}", f"{EN_PREFIX}/{col}"]

    if CLONE_DIR.exists():
        print("bilara-data already cloned, fetching latest...")
        subprocess.run(["git", "-C", str(CLONE_DIR), "fetch", "--depth=1", "origin", "HEAD"], check=True)
        subprocess.run(["git", "-C", str(CLONE_DIR), "reset", "--hard", "FETCH_HEAD"], check=True)
        subprocess.run(
            ["git", "-C", str(CLONE_DIR), "sparse-checkout", "set"] + paths,
            check=True
        )
        return

    print("Cloning bilara-data (sparse, depth=1)...")
    subprocess.run([
        "git", "clone", "--depth=1", "--filter=blob:none", "--sparse",
        REPO_URL, str(CLONE_DIR)
    ], check=True)
    subprocess.run(
        ["git", "-C", str(CLONE_DIR), "sparse-checkout", "set"] + paths,
        check=True
    )


def convert(collection: str, *, clone_dir: Path = CLONE_DIR, dump_dir: Path = DUMP_DIR) -> int:
    """
    Convert all bilara Pali+EN files for a collection into per-sutta dump JSONs.

    Handles both flat collections (DN, MN, SN, ITI — one sutta per file) and
    grouped files (AN — multiple suttas per file, DHP — multiple verses per file)
    by splitting on the sutta-id prefix (the part of each segment key before ':').
    """
    pali_dir = clone_dir / PALI_PREFIX / collection
    en_dir = clone_dir / EN_PREFIX / collection

    if not pali_dir.exists():
        print(f"  No Pali files found for {collection}, skipping.")
        return 0

    count = 0
    for pali_file in sorted(pali_dir.rglob("*_root-pli-ms.json")):
        rel = pali_file.relative_to(pali_dir)
        en_file = en_dir / str(rel).replace("_root-pli-ms.json", "_translation-en-sujato.json")
        if not en_file.exists():
            continue

        pali_segs = json.loads(pali_file.read_text(encoding="utf-8"))
        en_segs = json.loads(en_file.read_text(encoding="utf-8"))

        # Group segments by logical sutta id (key prefix before ':')
        suttas: dict[str, dict] = {}
        for key, pali_text in pali_segs.items():
            sutta_id = key.split(":")[0]
            if sutta_id not in suttas:
                suttas[sutta_id] = {}
            suttas[sutta_id][key] = pali_text

        for sutta_id, pali_verses in suttas.items():
            verses = []
            for i, (key, pali_text) in enumerate(pali_verses.items(), start=1):
                en_text = en_segs.get(key, "")
                if not pali_text.strip() and not en_text.strip():
                    continue
                verses.append({"number": i, "pali": pali_text, "english": en_text})

            if not verses:
                continue

            out = {"sutta_id": sutta_id.upper(), "verses": verses}
            out_path = dump_dir / f"{sutta_id}.json"
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            count += 1

    return count


def main():
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    sparse_clone()
    total = 0
    for col in COLLECTIONS + KN_COLLECTIONS:
        print(f"Converting {col.upper()}...")
        n = convert(col)
        print(f"  {n} suttas written.")
        total += n
    print(f"\nDone. {total} sutta files in {DUMP_DIR}")
    print("Next: python3 data/process_dumps.py")


if __name__ == "__main__":
    main()
