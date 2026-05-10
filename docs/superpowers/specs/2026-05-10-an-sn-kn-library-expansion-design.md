# Library Expansion: AN, SN, DHP, ITI

**Date:** 2026-05-10
**Status:** Approved

## Goal

Extend the Pali Canon search library from DN + MN to also include:
- Anguttara Nikaya (AN) — ~8,000 suttas across 11 nipatas
- Samyutta Nikaya (SN) — ~2,800 suttas across 56 samyuttas
- Dhammapada (DHP) — 423 verses (KN)
- Itivuttaka (ITI) — 112 suttas (KN)

## Files Changed

Two files change. Everything else (process_dumps.py, Qdrant indexing, search pipeline) is unchanged.

### 1. `data/fetch_bilara.py`

**Collections config:**
```python
COLLECTIONS = ["dn", "mn", "an", "sn"]
KN_COLLECTIONS = ["kn/dhp", "kn/iti"]
```

**`sparse_clone()` update:** adds all new Pali + EN paths to the sparse checkout set.

**`convert()` refactor:** The current implementation uses `glob("*_root-pli-ms.json")` (flat, one sutta per file). The new implementation:

1. Uses `rglob("*_root-pli-ms.json")` to traverse subdirectories (AN and SN have nipata/samyutta subdirs; ITI has vagga subdirs).
2. For each file, groups segments by their **sutta-id prefix** — the text before the first `:` in each JSON key. For example, keys `an1.1:0.1` and `an1.1:1.2` both belong to sutta `an1.1`; key `an1.2:1.0` belongs to `an1.2`. This splits AN's multi-sutta files correctly.
3. For each Pali file, resolves the mirror EN translation file by substituting the Pali prefix (`root/pli/ms/sutta`) with the EN prefix (`translation/en/sujato/sutta`) and replacing `_root-pli-ms.json` with `_translation-en-sujato.json`. Loads both files once, then for each logical sutta looks up EN segments by key (missing keys → empty string).
4. Writes one dump JSON per logical sutta: `an1.1.json`, `sn1.10.json`, `dhp1.json`, `iti1.json`.

`main()` iterates over `COLLECTIONS + KN_COLLECTIONS`.

**Note on DHP:** Dhammapada files group verse ranges (e.g. `dhp1-20`). The sutta-id prefix approach splits them into individual verses (`dhp1`, `dhp2`, ..., `dhp423`), giving fine-grained search granularity.

### 2. `backend/app/core/indexing.py`

Single regex change in `SuttaParser.parse()`:

```python
# Before
match = re.match(r"([a-zA-Z]+)(\d+)", sutta_id)
# After
match = re.match(r"([a-zA-Z]+)([\d.]+)", sutta_id)
```

This correctly formats dotted IDs: `AN1.1` → `AN 1.1`, `SN1.10` → `SN 1.10`, `DHP1` → `DHP 1`. Existing `DN1`/`MN1` behaviour is unchanged.

## Data Flow

```
fetch_bilara.py
  → sparse checkout AN/SN/KN paths from bilara-data
  → rglob all *_root-pli-ms.json files
  → group segments by sutta-id prefix
  → pair with EN translation segments
  → write data/dumps/an1.1.json, sn1.10.json, dhp1.json, iti1.json ...

process_dumps.py  (unchanged)
  → reads all JSON files in data/dumps/
  → SuttaParser.parse() creates chunks
  → EmbeddingManager encodes and upserts to Qdrant
  → resumes after interruption (already supported)
```

## Scale

| Collection | Logical suttas/units |
|---|---|
| AN | ~8,000 |
| SN | ~2,800 |
| DHP | 423 |
| ITI | 112 |
| **New total** | **~11,335** |

Re-indexing will take significant time. `process_dumps.py` supports resume — any interruption can be continued by re-running it.

## Error Handling

No new error handling needed. The existing skip-if-no-EN-file logic in `convert()` already handles any suttas that lack a Sujato translation.

## Testing

Existing `tests/backend/test_ingestion.py` covers the `SuttaParser` and `EmbeddingManager`. After the change:
- Add a test case for `SuttaParser.parse()` with a dotted sutta_id (e.g. `AN1.1`) verifying `AN 1.1` formatting.
- Smoke-test `fetch_bilara.py` by running it and checking that `data/dumps/` contains `an*.json`, `sn*.json`, `dhp*.json`, `iti*.json` files.
