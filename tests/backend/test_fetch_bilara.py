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


def test_convert_kn_iti_single_sutta(tmp_path):
    """ITI-style: one sutta per file, in a vagga subdirectory."""
    clone_dir = _make_bilara_fixture(
        tmp_path, "kn/iti", "vagga1",
        "iti1",
        pali_segs={"iti1:1.1": "ITI1 pali.", "iti1:1.2": "ITI1 pali cont."},
        en_segs={"iti1:1.1": "ITI1 english.", "iti1:1.2": "ITI1 english cont."},
    )
    dump_dir = tmp_path / "dumps"
    dump_dir.mkdir()
    count = _run_convert(clone_dir, "kn/iti", dump_dir)
    assert count == 1
    out = json.loads((dump_dir / "iti1.json").read_text())
    assert out["sutta_id"] == "ITI1"
    assert len(out["verses"]) == 2
    assert out["verses"][0]["pali"] == "ITI1 pali."


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
