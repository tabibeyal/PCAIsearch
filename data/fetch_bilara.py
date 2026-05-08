"""
Downloads DN + MN from bilara-data (sparse checkout) and converts to the
format expected by process_dumps.py:
  { "sutta_id": "DN1", "verses": [{"number": 1, "pali": "...", "english": "..."}, ...] }
"""
import json
import subprocess
from pathlib import Path

REPO_URL = "https://github.com/suttacentral/bilara-data.git"
CLONE_DIR = Path("/tmp/bilara-data")
DUMP_DIR = Path(__file__).parent / "dumps"

COLLECTIONS = ["dn", "mn"]

PALI_PREFIX = "root/pli/ms/sutta"
EN_PREFIX   = "translation/en/sujato/sutta"


def sparse_clone():
    if CLONE_DIR.exists():
        print("bilara-data already cloned, pulling latest...")
        subprocess.run(["git", "-C", str(CLONE_DIR), "pull", "--depth=1"], check=True)
        return
    print("Cloning bilara-data (sparse, depth=1)...")
    subprocess.run([
        "git", "clone", "--depth=1", "--filter=blob:none", "--sparse",
        REPO_URL, str(CLONE_DIR)
    ], check=True)
    paths = []
    for col in COLLECTIONS:
        paths += [f"{PALI_PREFIX}/{col}", f"{EN_PREFIX}/{col}"]
    subprocess.run(
        ["git", "-C", str(CLONE_DIR), "sparse-checkout", "set"] + paths,
        check=True
    )


def convert(collection: str):
    pali_dir = CLONE_DIR / PALI_PREFIX / collection
    en_dir   = CLONE_DIR / EN_PREFIX   / collection
    if not pali_dir.exists():
        print(f"  No Pali files found for {collection}, skipping.")
        return 0

    count = 0
    for pali_file in sorted(pali_dir.glob("*_root-pli-ms.json")):
        # e.g. dn10_root-pli-ms.json → sutta_id = dn10
        sutta_id = pali_file.name.replace("_root-pli-ms.json", "")
        en_file = en_dir / f"{sutta_id}_translation-en-sujato.json"
        if not en_file.exists():
            continue

        pali_segs = json.loads(pali_file.read_text(encoding="utf-8"))
        en_segs   = json.loads(en_file.read_text(encoding="utf-8"))

        verses = []
        for i, (key, pali_text) in enumerate(pali_segs.items(), start=1):
            english_text = en_segs.get(key, "")
            if not pali_text.strip() and not english_text.strip():
                continue
            verses.append({"number": i, "pali": pali_text, "english": english_text})

        if not verses:
            continue

        out = {"sutta_id": sutta_id.upper(), "verses": verses}
        out_path = DUMP_DIR / f"{sutta_id}.json"
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        count += 1

    return count


def main():
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    sparse_clone()
    total = 0
    for col in COLLECTIONS:
        print(f"Converting {col.upper()}...")
        n = convert(col)
        print(f"  {n} suttas written.")
        total += n
    print(f"\nDone. {total} sutta files in {DUMP_DIR}")
    print("Next: python3 data/process_dumps.py")


if __name__ == "__main__":
    main()
