# Spec: ExpansionPrompt v3 — Pāḷi Reference Table

**Date:** 2026-05-16
**Status:** Approved

---

## Problem

`ExpansionPrompt` v2 instructs the LLM to output correct Pāḷi terminology on Line 2, but the model frequently hallucinates or generates generic terms. The five hard misses (MN 21, SN 12.1, AN 3.65, DN 31, SN 22.59) are all caused by the LLM generating wrong or irrelevant Pāḷi, which floods BM25 with noise instead of signalling the correct passage. The curated dictionary (added separately) provides a deterministic fallback but does not fix the LLM output itself.

---

## Approach

Add a `v3` to `ExpansionPrompt.VERSIONS` that appends a 15-entry Pāḷi reference block to the existing v2 instructions. The LLM can use the table to look up the correct terms rather than guessing. v2 is left intact so existing tests continue to pass.

---

## v3 Prompt

v2 text (unchanged) followed by:

```
Pāḷi reference (use for Line 2):
- dependent origination / ignorance: paṭicca-samuppāda avijjā saṅkhārā viññāṇa taṇhā
- five aggregates / not-self: khandha rūpa vedanā saññā saṅkhārā viññāṇa anattā anicca
- Kālāma sutta / testing teachings: kālāmā anussava parampara itikirā takkahetu
- saw simile / patience under attack: kakacūpama khanti abyāpajjha mettā
- householder ethics / parents & family: sigālovāda mātāpitaro disa ācariya mitta
- four noble truths: cattāri ariyasaccāni dukkha samudaya nirodha magga
- noble eightfold path: sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta sammā-ājīva sammā-vāyāma sammā-sati sammā-samādhi
- mindfulness / breath: satipaṭṭhāna kāyānupassanā ānāpānasati
- jhāna / absorption: jhāna samādhi vitakka vicāra pīti sukha ekaggatā
- nibbāna / liberation: nibbāna vimutti asaṅkhata vimokkha
- brahmavihārās / loving-kindness: mettā karuṇā muditā upekkhā brahmavihāra
- precepts / ethics: sīla pāṇātipātā musāvādā adinnādānā
- three marks of existence: tilakkhaṇa anicca dukkha anattā
- kamma / intention / rebirth: kamma cetanā vipāka punabbhava saṃsāra
- middle way: majjhimā paṭipadā atitta atilīna
```

---

## Changes

| Action | File | Detail |
|--------|------|--------|
| Modify | `backend/app/services/search_pipeline.py` | Add `"v3"` to `ExpansionPrompt.VERSIONS`; switch default from `"v2"` to `"v3"` |
| Modify | `tests/backend/test_search_pipeline.py` | 2 new tests (see below) |

No new files. No new dependencies.

---

## Testing

Two new unit tests in `tests/backend/test_search_pipeline.py`:

1. `test_expansion_prompt_v3_contains_reference_block` — instantiate `ExpansionPrompt("v3")`, call `get_prompt()`, assert `"paṭicca-samuppāda"` and `"kakacūpama"` and `"sigālovāda"` are present in the string.

2. `test_search_pipeline_uses_v3_by_default` — instantiate `SearchPipeline()` without arguments, assert `pipeline.expansion_prompt.version == "v3"`.

Existing v2 tests must continue to pass unchanged.

---

## Benchmark Validation

Run `retrieval_benchmark.py --with-bm25 --with-expansion` and confirm:

| Criterion | Target |
|-----------|--------|
| Overall recall@10 | ≥ 53% (no regression) |
| Hard misses improved | at least one of MN 21, SN 12.1, AN 3.65, DN 31, SN 22.59 newly retrieved |

---

## Success Criteria

- All existing tests pass
- 2 new tests pass
- Benchmark ≥ 53%; at least one hard miss resolved
