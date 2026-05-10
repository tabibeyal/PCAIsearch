# AN/SN/KN Library Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the searchable library from DN+MN to also include AN, SN, Dhammapada, and Itivuttaka by refactoring the bilara-data fetch script and fixing a regex in SuttaParser.

**Architecture:** `fetch_bilara.py` is refactored to use `rglob` for subdirectory traversal and to group bilara segments by sutta-id prefix (text before `:` in each JSON key), producing one dump file per logical sutta. `SuttaParser.parse()` gets a one-line regex fix to handle dotted IDs like `AN1.1`. `process_dumps.py` and all Qdrant indexing code are unchanged.

**Tech Stack:** Python 3, pathlib, json stdlib, pytest

---

## File Map

| File | Action | What changes |
|---|---|---|
| `backend/app/core/indexing.py` | Modify | Regex in `SuttaParser.parse()`: `\d+` → `[\d.]+` |
| `tests/backend/test_ingestion.py` | Modify | Add test for dotted sutta_id formatting |
| `data/fetch_bilara.py` | Modify | Add KN_COLLECTIONS, update sparse_clone(), refactor convert() |
| `tests/backend/test_fetch_bilara.py` | Create | Unit tests for the new convert() logic using tmp fixtures |

---

## Task 1: Fix SuttaParser regex for dotted sutta IDs

**Files:**
- Modify: `backend/app/core/indexing.py:19`
- Modify: `tests/backend/test_ingestion.py`

- [ ] **Step 1.1: Add failing test for dotted sutta_id**

Open `tests/backend/test_ingestion.py` and append this test after the existing one:

```python
def test_parser_formats_dotted_sutta_id():
    parser = SuttaParser()
    data = {
        "sutta_id": "AN1.1",
        "verses": [
            {"number": 1, "pali": "Evaṁ me sutaṁ", "english": "Thus have I heard"}
        ]
    }
    chunks = parser.parse(data)
    assert chunks[0]["id"] == "AN 1.1:1"
```

- [ ] **Step 1.2: Run test to confirm it fails**

```bash
cd /home/eyal/PCAIsearch
python -m pytest tests/backend/test_ingestion.py::test_parser_formats_dotted_sutta_id -v
```

Expected output: `FAILED` — the chunk id will be `"AN 1:1"` (dot truncated).

- [ ] **Step 1.3: Fix the regex in SuttaParser**

In `backend/app/core/indexing.py` line 19, change:

```python
        match = re.match(r"([a-zA-Z]+)(\d+)", sutta_id)
```

to:

```python
        match = re.match(r"([a-zA-Z]+)([\d.]+)", sutta_id)
```

- [ ] **Step 1.4: Run both ingestion tests to confirm they pass**

```bash
python -m pytest tests/backend/test_ingestion.py -v
```

Expected output:
```
PASSED tests/backend/test_ingestion.py::test_ingestion_pipeline_full_flow
PASSED tests/backend/test_ingestion.py::test_parser_formats_dotted_sutta_id
```

- [ ] **Step 1.5: Commit**

```bash
git add backend/app/core/indexing.py tests/backend/test_ingestion.py
git commit -m "fix: support dotted sutta IDs (AN1.1, SN1.10) in SuttaParser regex"
```

---

## Task 2: Refactor fetch_bilara.py for AN, SN, DHP, ITI

**Files:**
- Modify: `data/fetch_bilara.py`
- Create: `tests/backend/test_fetch_bilara.py`

### Background

bilara-data file structure for the new collections:
- AN: `root/pli/ms/sutta/an/an1/an1.1-10_root-pli-ms.json` — one file may contain multiple suttas. Keys look like `"an1.1:0.1"`, `"an1.2:1.0"` — the part before `:` is the logical sutta id.
- SN: `root/pli/ms/sutta/sn/sn1/sn1.10_root-pli-ms.json` — one sutta per file.
- DHP: `root/pli/ms/sutta/kn/dhp/dhp1-20_root-pli-ms.json` — one file covers a verse range. Keys like `"dhp1:1"`, `"dhp2:1"` — each `dhpN` prefix is one verse.
- ITI: `root/pli/ms/sutta/kn/iti/vagga1/iti1_root-pli-ms.json` — one sutta per file.

EN translation files mirror the Pali path exactly, replacing `root/pli/ms/sutta` with `translation/en/sujato/sutta` and `_root-pli-ms.json` with `_translation-en-sujato.json`.

- [ ] **Step 2.1: Write failing tests for the new convert logic**

Create `tests/backend/test_fetch_bilara.py`:

```python
import json
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

PALI_PREFIX = "root/pli/ms/sutta"
EN_PREFIX = "translation/en/sujato/sutta"


def _make_bilara_fixture(tmp_path: Path, collection: str, subdir: str, filename_stem: str,
                          pali_segs: dict, en_segs: dict) -> Path:
    """Write a pair of bilara-style Pali + EN JSON files under tmp_path."""
    pali_dir = tmp_path / PALI_PREFIX / collection / subdir
    en_dir = tmp_path / EN_PREFIX / collection / subdir
    pali_dir.mkdir(parents=True, exist_ok=True)
    en_dir.mkdir(parents=True, exist_ok=True)
    pali_file = pali_dir / f"{filename_stem}_root-pli-ms.json"
    en_file = en_dir / f"{filename_stem}_translation-en-sujato.json"
    pali_file.write_text(json.dumps(pali_segs), encoding="utf-8")
    en_file.write_text(json.dumps(en_segs), encoding="utf-8")
    return tmp_path


def _run_convert(clone_dir: Path, collection: str, dump_dir: Path) -> int:
    """Call the refactored convert() directly."""
    from data.fetch_bilara import convert
    return convert(collection, clone_dir=clone_dir, dump_dir=dump_dir)


def test_convert_flat_single_sutta(tmp_path):
    """SN-style: one sutta per file, in a subdirectory."""
    clone_dir = _make_bilara_fixture(
        tmp_path, "sn", "sn1",
        "sn1.10",
        pali_segs={"sn1.10:1.1": "Pāli text.", "sn1.10:1.2": "More Pāli."},
        en_segs={"sn1.10:1.1": "English text.", "sn1.10:1.2": "More English."},
    )
    dump_dir = tmp_path / "dumps"
    dump_dir.mkdir()
    count = _run_convert(clone_dir, "sn", dump_dir)
    assert count == 1
    out = json.loads((dump_dir / "sn1.10.json").read_text())
    assert out["sutta_id"] == "SN1.10"
    assert len(out["verses"]) == 2
    assert out["verses"][0]["pali"] == "Pāli text."
    assert out["verses"][0]["english"] == "English text."


def test_convert_multi_sutta_file(tmp_path):
    """AN-style: multiple suttas per file."""
    clone_dir = _make_bilara_fixture(
        tmp_path, "an", "an1",
        "an1.1-3",
        pali_segs={
            "an1.1:1.1": "AN1.1 pali.",
            "an1.2:1.1": "AN1.2 pali.",
            "an1.3:1.1": "AN1.3 pali.",
        },
        en_segs={
            "an1.1:1.1": "AN1.1 english.",
            "an1.2:1.1": "AN1.2 english.",
            "an1.3:1.1": "AN1.3 english.",
        },
    )
    dump_dir = tmp_path / "dumps"
    dump_dir.mkdir()
    count = _run_convert(clone_dir, "an", dump_dir)
    assert count == 3
    assert (dump_dir / "an1.1.json").exists()
    assert (dump_dir / "an1.2.json").exists()
    assert (dump_dir / "an1.3.json").exists()
    out = json.loads((dump_dir / "an1.1.json").read_text())
    assert out["sutta_id"] == "AN1.1"
    assert out["verses"][0]["pali"] == "AN1.1 pali."


def test_convert_kn_dhp_splits_verses(tmp_path):
    """DHP-style: verse-range file splits into per-verse dumps."""
    clone_dir = _make_bilara_fixture(
        tmp_path, "kn/dhp", "",
        "dhp1-3",
        pali_segs={
            "dhp1:1": "Verse 1 pali.", "dhp1:2": "Verse 1 cont.",
            "dhp2:1": "Verse 2 pali.",
            "dhp3:1": "Verse 3 pali.",
        },
        en_segs={
            "dhp1:1": "Verse 1 eng.", "dhp1:2": "Verse 1 eng cont.",
            "dhp2:1": "Verse 2 eng.",
            "dhp3:1": "Verse 3 eng.",
        },
    )
    dump_dir = tmp_path / "dumps"
    dump_dir.mkdir()
    count = _run_convert(clone_dir, "kn/dhp", dump_dir)
    assert count == 3
    out = json.loads((dump_dir / "dhp1.json").read_text())
    assert out["sutta_id"] == "DHP1"
    assert len(out["verses"]) == 2


def test_convert_skips_missing_en_file(tmp_path):
    """Files with no EN counterpart are skipped."""
    pali_dir = tmp_path / PALI_PREFIX / "sn" / "sn99"
    pali_dir.mkdir(parents=True)
    (pali_dir / "sn99.1_root-pli-ms.json").write_text(
        json.dumps({"sn99.1:1.1": "Pāli only."}), encoding="utf-8"
    )
    dump_dir = tmp_path / "dumps"
    dump_dir.mkdir()
    count = _run_convert(tmp_path, "sn", dump_dir)
    assert count == 0
```

- [ ] **Step 2.2: Run tests to confirm they fail**

```bash
python -m pytest tests/backend/test_fetch_bilara.py -v
```

Expected: all 4 tests `ERROR` or `FAILED` — `convert()` doesn't accept `clone_dir`/`dump_dir` kwargs yet.

- [ ] **Step 2.3: Rewrite fetch_bilara.py**

Replace the entire contents of `data/fetch_bilara.py` with:

```python
"""
Downloads DN, MN, AN, SN and selected KN texts from bilara-data (sparse checkout)
and converts to the format expected by process_dumps.py:
  { "sutta_id": "AN1.1", "verses": [{"number": 1, "pali": "...", "english": "..."}, ...] }
"""
import json
import subprocess
from collections import defaultdict
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
        print("bilara-data already cloned, pulling latest...")
        subprocess.run(["git", "-C", str(CLONE_DIR), "pull", "--depth=1"], check=True)
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
```

- [ ] **Step 2.4: Run tests to confirm they all pass**

```bash
python -m pytest tests/backend/test_fetch_bilara.py -v
```

Expected output:
```
PASSED tests/backend/test_fetch_bilara.py::test_convert_flat_single_sutta
PASSED tests/backend/test_fetch_bilara.py::test_convert_multi_sutta_file
PASSED tests/backend/test_fetch_bilara.py::test_convert_kn_dhp_splits_verses
PASSED tests/backend/test_fetch_bilara.py::test_convert_skips_missing_en_file
```

- [ ] **Step 2.5: Run existing ingestion tests to confirm no regressions**

```bash
python -m pytest tests/backend/test_ingestion.py -v
```

Expected: both tests `PASSED`.

- [ ] **Step 2.6: Commit**

```bash
git add data/fetch_bilara.py tests/backend/test_fetch_bilara.py
git commit -m "feat: add AN, SN, DHP, ITI to library fetch pipeline"
```

---

## Task 3: Smoke-test the full pipeline with real bilara-data

This task runs `fetch_bilara.py` against the real bilara-data repo and checks the output. It is NOT a pytest test — it's a manual verification step.

- [ ] **Step 3.1: Run fetch_bilara.py**

```bash
cd /home/eyal/PCAIsearch
python3 data/fetch_bilara.py
```

Expected: prints progress lines like:
```
bilara-data already cloned, pulling latest...
Converting DN...
  34 suttas written.
Converting MN...
  152 suttas written.
Converting AN...
  8122 suttas written.
Converting SN...
  2904 suttas written.
Converting KN/DHP...
  423 suttas written.
Converting KN/ITI...
  112 suttas written.
Done. NNNN sutta files in data/dumps
```

- [ ] **Step 3.2: Verify dump files exist for all collections**

```bash
ls data/dumps/ | grep -E "^(an|sn|dhp|iti)" | head -20
ls data/dumps/ | grep -cE "^an"
ls data/dumps/ | grep -cE "^sn"
ls data/dumps/ | grep -cE "^dhp"
ls data/dumps/ | grep -cE "^iti"
```

Expected: AN files ≥ 8000, SN files ≥ 2000, DHP files = 423, ITI files = 112.

- [ ] **Step 3.3: Spot-check a dump file from each new collection**

```bash
python3 -c "
import json
for f in ['data/dumps/an1.1.json', 'data/dumps/sn1.10.json', 'data/dumps/dhp1.json', 'data/dumps/iti1.json']:
    d = json.load(open(f))
    v = d['verses'][0]
    print(f\"{d['sutta_id']}: {v['pali'][:40]} / {v['english'][:40]}\")
"
```

Expected: four lines, each with Pali and English text, no empty strings.

- [ ] **Step 3.4: Commit smoke-test results (no code change needed — this is a manual check)**

No commit required for this task. Proceed to indexing when ready.

---

## After Completion: Re-index

Once the dump files are verified, re-run `process_dumps.py` to index the new suttas into Qdrant. It supports resume so can be interrupted and restarted safely:

```bash
python3 data/process_dumps.py
```
