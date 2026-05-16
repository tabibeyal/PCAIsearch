# ExpansionPrompt v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `ExpansionPrompt` v3 — identical to v2 but with a 15-entry Pāḷi reference table appended, so the LLM can look up correct terms instead of guessing.

**Architecture:** A new `"v3"` key is added to `ExpansionPrompt.VERSIONS` in `search_pipeline.py`. The v3 string is the v2 string concatenated with a reference block. The pipeline default switches from `"v2"` to `"v3"`. v2 is untouched — all existing tests continue to pass.

**Tech Stack:** Python stdlib only. No new dependencies.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/app/services/search_pipeline.py` | Add `"v3"` to `VERSIONS`; switch `__init__` default to `"v3"` |
| Modify | `tests/backend/test_search_pipeline.py` | 2 new unit tests |

---

## Task 1: Add v3 to ExpansionPrompt and switch default

**Files:**
- Modify: `backend/app/services/search_pipeline.py`
- Modify: `tests/backend/test_search_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/backend/test_search_pipeline.py`:

```python
def test_expansion_prompt_v3_contains_reference_block():
    prompt = ExpansionPrompt("v3").get_prompt()
    assert "paṭicca-samuppāda" in prompt
    assert "kakacūpama" in prompt
    assert "sigālovāda" in prompt


def test_search_pipeline_uses_v3_by_default():
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()
    assert pipeline.expansion_prompt.version == "v3"
```

- [ ] **Step 2: Run failing tests**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_search_pipeline.py::test_expansion_prompt_v3_contains_reference_block tests/backend/test_search_pipeline.py::test_search_pipeline_uses_v3_by_default -v
```

Expected: both FAIL — `"v3"` not in `VERSIONS`.

- [ ] **Step 3: Add v3 to `ExpansionPrompt.VERSIONS` and switch default**

In `backend/app/services/search_pipeline.py`, find the `VERSIONS` dict (currently ends after the `"v2"` entry) and add `"v3"` immediately after:

```python
        "v3": (
            "You are a search query expander for a Pali Canon database. "
            "Given a user query, output exactly 2 search strings on separate lines.\n"
            "Line 1 — English passage vocabulary: concrete words likely to appear verbatim in a sutta "
            "verse. Do NOT rephrase the question. Think: what exact words would a monk say in this passage?\n"
            "Line 2 — Pali doctrinal term cluster: the canonical Pali terminology for the concept, "
            "space-separated and transliterated (e.g. avijja sankharā viññāna paticca-samuppāda). "
            "Proper names of communities or persons are allowed (e.g. kālāmā). "
            "Do NOT include sutta numbers.\n"
            "Output exactly two lines, no numbering, no explanation. "
            "The two lines must be maximally distinct from each other and from the original query.\n\n"
            "Pāḷi reference (use for Line 2):\n"
            "- dependent origination / ignorance: paṭicca-samuppāda avijjā saṅkhārā viññāṇa taṇhā\n"
            "- five aggregates / not-self: khandha rūpa vedanā saññā saṅkhārā viññāṇa anattā anicca\n"
            "- Kālāma sutta / testing teachings: kālāmā anussava parampara itikirā takkahetu\n"
            "- saw simile / patience under attack: kakacūpama khanti abyāpajjha mettā\n"
            "- householder ethics / parents & family: sigālovāda mātāpitaro disa ācariya mitta\n"
            "- four noble truths: cattāri ariyasaccāni dukkha samudaya nirodha magga\n"
            "- noble eightfold path: sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta "
            "sammā-ājīva sammā-vāyāma sammā-sati sammā-samādhi\n"
            "- mindfulness / breath: satipaṭṭhāna kāyānupassanā ānāpānasati\n"
            "- jhāna / absorption: jhāna samādhi vitakka vicāra pīti sukha ekaggatā\n"
            "- nibbāna / liberation: nibbāna vimutti asaṅkhata vimokkha\n"
            "- brahmavihārās / loving-kindness: mettā karuṇā muditā upekkhā brahmavihāra\n"
            "- precepts / ethics: sīla pāṇātipātā musāvādā adinnādānā\n"
            "- three marks of existence: tilakkhaṇa anicca dukkha anattā\n"
            "- kamma / intention / rebirth: kamma cetanā vipāka punabbhava saṃsāra\n"
            "- middle way: majjhimā paṭipadā atitta atilīna"
        ),
```

Then change the `__init__` default from `"v2"` to `"v3"`:

```python
    def __init__(self, version: str = "v3"):
```

- [ ] **Step 4: Run the two new tests**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_search_pipeline.py::test_expansion_prompt_v3_contains_reference_block tests/backend/test_search_pipeline.py::test_search_pipeline_uses_v3_by_default -v
```

Expected: both PASS.

- [ ] **Step 5: Run the full test suite**

```bash
PYTHONPATH=. python -m pytest tests/backend/ -q --ignore=tests/backend/test_e2e_pipeline.py
```

Expected: ≥ 132 passed (130 existing + 2 new), same 6 pre-existing errors in `test_api.py`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/search_pipeline.py tests/backend/test_search_pipeline.py
git commit -m "feat: add ExpansionPrompt v3 with Pāḷi reference table, switch pipeline default"
```

---

## Task 2: Benchmark validation

**Files:**
- Run only: `tests/backend/retrieval_benchmark.py`

- [ ] **Step 1: Run the benchmark**

```bash
PYTHONPATH=. python3 tests/backend/retrieval_benchmark.py --with-bm25 --with-expansion
```

Requires `NVIDIA_API_KEY` in environment and a running Qdrant instance. Takes a few minutes.

- [ ] **Step 2: Verify results**

| Criterion | Target |
|-----------|--------|
| Overall recall@10 | ≥ 53% (8/15) — no regression |
| Hard misses | At least one of MN 21, SN 12.1, AN 3.65, DN 31, SN 22.59 newly retrieved |

- [ ] **Step 3: Update HANDOFF.md**

Add a row to the recall scoreboard:

```
| Expansion + BM25 + Pāḷi dict + v3 prompt | X/5 | X/5 | X/5 | X/15 (X%) |
```

Update the "Remaining hard misses" section to reflect which cases are now resolved.

- [ ] **Step 4: Commit**

```bash
git add HANDOFF.md
git commit -m "docs: update HANDOFF with ExpansionPrompt v3 benchmark results"
```
