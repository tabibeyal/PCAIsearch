# Spec: Curated Pāḷi Term Dictionary

**Date:** 2026-05-16
**Status:** Approved

---

## Problem

The Gemma expansion model frequently generates hallucinated or garbled Pāḷi terminology. This causes BM25 to flood the candidate pool with irrelevant matches (e.g., pāṇātipātā for a query about lying) and leaves five hard misses unreachable because the correct Pāḷi cluster never appears in the expanded variants. The five persistent misses are: MN 21, SN 12.1, AN 3.65, DN 31, SN 22.59.

---

## Approach

Inject a deterministic 3rd expansion variant from a hand-curated dictionary. The pipeline currently generates 2 LLM variants; when a dictionary match is found, a 3rd variant (correct Pāḷi terms) is appended. All variants flow through the existing BM25 × N → dense × N → RRF fusion path with no other changes.

The original user query (not the LLM variants) is used for lookup — it is the most trustworthy signal.

---

## Components

### `backend/app/services/pali_dictionary.py`

A module containing:

- A list of ~50–80 `DictionaryEntry` objects, each with:
  - `keywords: List[str]` — lowercase English trigger words; any match fires the entry
  - `pali: str` — space-separated canonical Pāḷi terms to inject as a BM25 search string
  - `label: str` — human-readable name for logging/debugging

- `lookup(query: str) -> Optional[str]` — lowercases the query, iterates entries, returns the first match's `pali` string or `None` if no entry fires.

**Dictionary coverage (~50–80 entries across these clusters):**

| Cluster | Example entries |
|---------|----------------|
| Four Noble Truths | dukkha, samudaya, nirodha, magga |
| Dependent Origination | paṭicca-samuppāda, avijjā, saṅkhārā, viññāṇa, nāmarūpa, salāyatana, phassa, vedanā, taṇhā, upādāna, bhava, jāti, jarāmaraṇa |
| Eightfold Path | sammā-diṭṭhi, sammā-saṅkappa, sammā-vācā, sammā-kammanta, sammā-ājīva, sammā-vāyāma, sammā-sati, sammā-samādhi |
| Five Aggregates | khandha, rūpa, vedanā, saññā, saṅkhāra, viññāṇa |
| Precepts | sīla, pāṇātipātā, adinnādānā, kāmesumicchācārā, musāvādā, surāmeraya |
| Jhāna / Meditation | jhāna, samādhi, samatha, vipassanā, vitakka, vicāra, pīti, sukha |
| Brahmavihārās | mettā, karuṇā, muditā, upekkhā, brahmavihāra |
| Wisdom / Insight | paññā, vijjā, anicca, dukkha, anattā, tilakkhaṇa |
| Kālāma / Epistemology | kālāmā, anussava, parampara, itikirā |
| Monastic / Saṅgha | vinaya, bhikkhu, bhikkhunī, saṅgha, pātimokkha |
| Loving-kindness | mettā, karuṇā, sattā, sukhī |
| Impermanence / Death | anicca, maraṇa, jarā, vipariṇāma |
| Similes (idiomatic) | araṇī, kakacūpama (saw simile), raft simile, poison arrow |

### Integration in `search_pipeline.py`

In `expand_query()`, after the LLM call produces 2 variants:

```
pali_hit = lookup(original_query)
if pali_hit:
    variants.append(pali_hit)
return variants  # 2 or 3 elements
```

No other changes — the downstream BM25 × N and dense × N loops already handle variable-length variant lists.

---

## Testing

### Unit tests (`tests/backend/test_pali_dictionary.py`)

- Known query hits the expected entry (SN 12.1 → paṭicca-samuppāda cluster)
- Any keyword in a multi-keyword entry fires correctly
- Unrecognised query returns `None`
- Lookup is case-insensitive

### Integration test (`tests/backend/test_search_pipeline.py`)

- Mock `lookup()` returning a Pāḷi string; assert `expand_query()` returns 3 elements with the Pāḷi string appended
- Mock `lookup()` returning `None`; assert `expand_query()` returns 2 elements unchanged

### Benchmark validation

Run `retrieval_benchmark.py --with-bm25 --with-expansion` and confirm:
- Overall recall ≥ 53% (no regression)
- SN 12.1 or AN 3.65 newly retrieved (targeted improvement)
- MN 61 not further regressed

---

## Success Criteria

- Recall@10 stays ≥ 53%
- At least one of the 5 hard misses is newly retrieved
- MN 61 does not drop further
- Dictionary is readable and maintainable as a plain Python file

---

## Out of Scope

- Embedding-based or LLM-based lookup (deferred)
- Vinaya-specific terminology (deferred until Vinaya ingestion)
- Comprehensive canonical coverage (this spec targets ~50–80 high-value entries)
