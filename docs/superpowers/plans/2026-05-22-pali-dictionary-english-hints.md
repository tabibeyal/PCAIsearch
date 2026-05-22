# Pali Dictionary — English Hints & Keyword Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `english_hint` strings to 11 dictionary entries that currently lack them, and add 6 missing standalone Pali term keywords — so that `lookup_english()` returns a verbatim sutta-style passage hint for common doctrinal queries like "anicca", "nibbana", "dukkha", "panna".

**Architecture:** All changes are confined to `backend/app/services/pali_dictionary.py` and its test file. No architectural change, no re-indexing. The `english_hint` strings are in Thanissaro Bhikkhu-style sutta English — the same vocabulary found in the indexed documents — so the reranker (ms-marco-MiniLM-L-6-v2) can use them to score retrieved passages against the query. Note: the "Ignorance / avijjā" entry is NOT in scope for english_hint work because all its keywords ("avijja", "ignorance") are intercepted first by the "Dependent Origination" entry, which already has a hint.

**Tech Stack:** Python, pytest. No external dependencies.

---

## File Map

- **Modify:** `backend/app/services/pali_dictionary.py` — add `english_hint` to 11 entries; add keywords to 6 entries
- **Modify:** `tests/backend/test_pali_dictionary.py` — fix 1 stale test; add tests for new behaviors

---

### Task 1: Fix the pre-existing stale test

**Current state:** 16 passing, 1 failing. `test_lookup_english_no_hint_returns_none` asserts `lookup_english("four noble truths") is None`, but that entry already has an `english_hint`. Fix it to use "five precepts", which has no hint and will not get one in this feature.

**Files:**
- Modify: `tests/backend/test_pali_dictionary.py:96-98`

- [ ] **Step 1: Confirm current failure**

Run: `PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py::test_lookup_english_no_hint_returns_none -v`

Expected output:
```
FAILED ...test_lookup_english_no_hint_returns_none
AssertionError: assert 'noble truth stress suffering...' is None
```

- [ ] **Step 2: Fix the stale test**

In `tests/backend/test_pali_dictionary.py`, replace the body of `test_lookup_english_no_hint_returns_none`:

```python
def test_lookup_english_no_hint_returns_none():
    # "five precepts" matches the entry but it has no english_hint
    result = lookup_english("five precepts")
    assert result is None
```

- [ ] **Step 3: Run to verify all 17 pass**

Run: `PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -v`

Expected: 17 passed, 0 failed

- [ ] **Step 4: Commit**

```bash
git add tests/backend/test_pali_dictionary.py
git commit -m "test: fix stale lookup_english test for four noble truths"
```

---

### Task 2: Add missing standalone Pali keyword tests (red phase)

Write failing tests for the 6 standalone Pali terms that currently return `None` from `lookup()`.

**Files:**
- Modify: `tests/backend/test_pali_dictionary.py` — append new tests

- [ ] **Step 1: Append the failing tests**

Add to the end of `tests/backend/test_pali_dictionary.py`:

```python
# --- Part 2: standalone Pali keyword coverage ---

def test_lookup_bare_dukkha():
    result = lookup("dukkha")
    assert result is not None
    assert "dukkha" in result


def test_lookup_bare_samadhi():
    result = lookup("samadhi")
    assert result is not None
    assert "samādhi" in result


def test_lookup_bare_panna():
    result = lookup("panna")
    assert result is not None
    assert "paññā" in result


def test_lookup_bare_sati():
    result = lookup("sati")
    assert result is not None
    assert "sati" in result


def test_lookup_bare_tanha():
    result = lookup("tanha")
    assert result is not None
    assert "taṇhā" in result


def test_lookup_bare_raga():
    result = lookup("raga")
    assert result is not None
    assert "rāga" in result
```

- [ ] **Step 2: Run to verify all 6 new tests fail**

Run: `PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -v -k "bare"`

Expected: 6 failed, each with `AssertionError: assert None is not None`

---

### Task 3: Implement Part 2 — missing standalone keywords

Add 6 missing Pali terms as keywords to their respective entries in `backend/app/services/pali_dictionary.py`.

**Files:**
- Modify: `backend/app/services/pali_dictionary.py`

- [ ] **Step 1: Add "dukkha" to the Suffering / dukkha entry**

Find the entry with `label="Suffering / dukkha"`. Change its `keywords` list from:

```python
keywords=["stress", "suffering", "unsatisfactoriness", "cause of suffering", "origin of suffering", "cause of stress"],
```

to:

```python
keywords=["stress", "suffering", "unsatisfactoriness", "cause of suffering", "origin of suffering", "cause of stress", "dukkha"],
```

- [ ] **Step 2: Add "samadhi", "samādhi" to the Concentration / samādhi entry**

Find the entry with `label="Concentration / samādhi"`. Change its `keywords` list from:

```python
keywords=[
    "concentration", "one-pointedness", "mental unification",
    "stillness of mind", "calm abiding", "serenity",
    "unified mind", "collected mind",
],
```

to:

```python
keywords=[
    "concentration", "one-pointedness", "mental unification",
    "stillness of mind", "calm abiding", "serenity",
    "unified mind", "collected mind",
    "samadhi", "samādhi",
],
```

- [ ] **Step 3: Add "panna", "paññā" to the Wisdom / insight entry**

Find the entry with `label="Wisdom / insight"`. Change its `keywords` list from:

```python
keywords=[
    "wisdom", "insight", "discernment", "clear seeing",
    "true knowledge", "seeing things as they are",
],
```

to:

```python
keywords=[
    "wisdom", "insight", "discernment", "clear seeing",
    "true knowledge", "seeing things as they are",
    "panna", "paññā",
],
```

- [ ] **Step 4: Add "sati" to the Mindfulness / satipaṭṭhāna entry**

Find the entry with `label="Mindfulness / satipaṭṭhāna"`. Its `keywords` list currently ends with `"mindfulness of mind"`. Add `"sati"` after it:

```python
    "mindfulness of body", "mindfulness of feelings", "mindfulness of mind",
    "sati",
```

- [ ] **Step 5: Add "tanha", "taṇhā" to the Three types of craving entry**

Find the entry with `label="Three types of craving"`. Its `keywords` list currently ends with `"craving for non-existence"`. Add after it:

```python
    "craving for non-existence",
    "tanha", "taṇhā",
```

- [ ] **Step 6: Add "raga", "rāga" to the Defilements / kilesa entry**

Find the entry with `label="Defilements / kilesa"`. Change its `keywords` list from:

```python
keywords=[
    "defilement", "defilements", "kilesa", "mental defilement",
    "unwholesome", "roots of unwholesomeness", "greed hate delusion",
    "lobha dosa moha",
],
```

to:

```python
keywords=[
    "defilement", "defilements", "kilesa", "mental defilement",
    "unwholesome", "roots of unwholesomeness", "greed hate delusion",
    "lobha dosa moha",
    "raga", "rāga",
],
```

- [ ] **Step 7: Run to verify all 6 new tests pass**

Run: `PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -v -k "bare"`

Expected: 6 passed

- [ ] **Step 8: Run full test suite**

Run: `PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -v`

Expected: 23 passed, 0 failed

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/pali_dictionary.py tests/backend/test_pali_dictionary.py
git commit -m "feat: add standalone Pali term keywords to pali_dictionary entries"
```

---

### Task 4: Add english_hint tests (red phase)

Write failing tests for 11 entries that currently have `english_hint=None`.

**Note on "anatta":** `lookup_english("anatta")` hits "Three Marks of Existence" (entry #8), not "Not-self / anattā" (entry #40), because Three Marks comes first and also has "anatta" as a keyword. The hint is added to Three Marks; the Not-self entry is separately testable via "no self".

**Note on "avijja":** `lookup_english("avijja")` already returns a non-None value — it hits the "Dependent Origination" entry (entry #1) which has both "avijja" as a keyword and a pre-existing `english_hint`. No new test or implementation needed for avijja.

**Files:**
- Modify: `tests/backend/test_pali_dictionary.py` — append new tests

- [ ] **Step 1: Append the failing tests**

Add to the end of `tests/backend/test_pali_dictionary.py`:

```python
# --- Part 1: english_hint coverage ---

def test_lookup_english_anicca():
    # hits "Three Marks of Existence" — currently no english_hint
    result = lookup_english("anicca")
    assert result is not None
    assert "impermanent" in result


def test_lookup_english_dukkha():
    # hits "Suffering / dukkha" — currently no english_hint
    result = lookup_english("dukkha")
    assert result is not None
    assert "suffering" in result


def test_lookup_english_nibbana():
    # hits "Nibbāna / liberation" — currently no english_hint
    result = lookup_english("nibbana")
    assert result is not None
    assert "unborn" in result


def test_lookup_english_anatta_hits_three_marks():
    # "anatta" hits Three Marks of Existence first (entry #8)
    result = lookup_english("anatta")
    assert result is not None
    assert "not-self" in result


def test_lookup_english_no_self_hits_not_self_entry():
    # "no self" hits "Not-self / anattā" — currently no english_hint
    result = lookup_english("no self")
    assert result is not None
    assert "not-self" in result


def test_lookup_english_kamma():
    # hits "Kamma / rebirth" — currently no english_hint
    result = lookup_english("kamma")
    assert result is not None
    assert "actions" in result


def test_lookup_english_samadhi():
    # hits "Concentration / samādhi" — currently no english_hint
    result = lookup_english("samadhi")
    assert result is not None
    assert "concentrated" in result


def test_lookup_english_sila():
    # hits "Ethical conduct / sīla" — currently no english_hint
    result = lookup_english("sila")
    assert result is not None
    assert "virtue" in result


def test_lookup_english_panna():
    # hits "Wisdom / insight" — currently no english_hint
    result = lookup_english("panna")
    assert result is not None
    assert "discernment" in result


def test_lookup_english_citta():
    # hits "Mind / citta" via its specific keyword — currently no english_hint
    result = lookup_english("mind is the forerunner")
    assert result is not None
    assert "mind is the forerunner" in result


def test_lookup_english_kilesa():
    # hits "Defilements / kilesa" — currently no english_hint
    result = lookup_english("kilesa")
    assert result is not None
    assert "greed" in result


def test_lookup_english_middle_way():
    # hits "Middle Way" — currently no english_hint
    result = lookup_english("middle way")
    assert result is not None
    assert "two extremes" in result
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -v -k "lookup_english_anicca or lookup_english_dukkha or lookup_english_nibbana or lookup_english_anatta or lookup_english_no_self or lookup_english_kamma or lookup_english_samadhi or lookup_english_sila or lookup_english_panna or lookup_english_citta or lookup_english_kilesa or lookup_english_middle_way"`

Expected: 12 failed, each with `AssertionError: assert None is not None`

---

### Task 5: Implement Part 1 — add english_hints to 11 entries

**Files:**
- Modify: `backend/app/services/pali_dictionary.py`

**Hint language rule:** Every hint must use sutta-translation vocabulary (Thanissaro Bhikkhu style). The reranker matches the hint against document text verbatim — modern paraphrase degrades scoring.

- [ ] **Step 1: Add english_hint to "Three Marks of Existence"**

Find the entry with `label="Three Marks of Existence"`. It currently ends with:

```python
    pali="tilakkhaṇa anicca dukkha anattā sabbe saṅkhārā vipariṇāma",
),
```

Change to:

```python
    pali="tilakkhaṇa anicca dukkha anattā sabbe saṅkhārā vipariṇāma",
    english_hint="form is impermanent feeling is impermanent all fabrications are impermanent subject to change suffering not-self this is not mine I am not this this is not my self",
),
```

- [ ] **Step 2: Add english_hint to "Suffering / dukkha"**

Find the entry with `label="Suffering / dukkha"`. It currently ends with:

```python
    pali="dukkha samudaya taṇhā upādāna bhava",
),
```

Change to:

```python
    pali="dukkha samudaya taṇhā upādāna bhava",
    english_hint="birth is suffering aging is suffering death is suffering sorrow lamentation pain grief despair not getting what one wants is suffering the five aggregates of clinging are suffering",
),
```

- [ ] **Step 3: Add english_hint to "Nibbāna / liberation"**

Find the entry with `label="Nibbāna / liberation"`. It currently ends with:

```python
    pali="nibbāna vimutti vimokkha sacchikiriyā asaṅkhata",
),
```

Change to:

```python
    pali="nibbāna vimutti vimokkha sacchikiriyā asaṅkhata",
    english_hint="unborn unbecome unmade unconditioned there would be no escape from what is born become made conditioned deathless cessation unbinding freed released",
),
```

- [ ] **Step 4: Add english_hint to "Not-self / anattā"**

Find the entry with `label="Not-self / anattā"`. It currently ends with:

```python
    pali="anattā sabbe dhammā anattā khandha ahaṃkāra",
),
```

Change to:

```python
    pali="anattā sabbe dhammā anattā khandha ahaṃkāra",
    english_hint="form is not-self if form were self form would not lead to affliction this is not mine I am not this this is not my self feeling perception fabrications consciousness not-self",
),
```

- [ ] **Step 5: Add english_hint to "Kamma / rebirth"**

Find the entry with `label="Kamma / rebirth"`. It currently ends with:

```python
    pali="kamma cetanā vipāka punabbhava saṃsāra",
),
```

Change to:

```python
    pali="kamma cetanā vipāka punabbhava saṃsāra",
    english_hint="beings are owners of their actions heirs of their actions actions are the womb from which they are born whatever actions they do good or bad they will inherit",
),
```

- [ ] **Step 6: Add english_hint to "Concentration / samādhi"**

Find the entry with `label="Concentration / samādhi"`. It currently ends with:

```python
    pali="samādhi samatha cetaso ekodibhāva",
),
```

Change to:

```python
    pali="samādhi samatha cetaso ekodibhāva",
    english_hint="unified mind concentrated one-pointed seclusion rapture pleasure equanimity developed cultivated noble right concentration made much of",
),
```

- [ ] **Step 7: Add english_hint to "Ethical conduct / sīla"**

Find the entry with `label="Ethical conduct / sīla"`. It currently ends with:

```python
    pali="sīla pārisuddhisīla ājīvapārisuddhisīla",
),
```

Change to:

```python
    pali="sīla pārisuddhisīla ājīvapārisuddhisīla",
    english_hint="virtue training rule of training restraint refraining abstaining purified upright blameless praised by the wise bodily verbal mental conduct",
),
```

- [ ] **Step 8: Add english_hint to "Wisdom / insight"**

Find the entry with `label="Wisdom / insight"`. It currently ends with:

```python
    pali="paññā vijjā ñāṇa dassana yathābhūta",
),
```

Change to:

```python
    pali="paññā vijjā ñāṇa dassana yathābhūta",
    english_hint="knowing and seeing things as they actually are discernment clear seeing understanding arising and passing away impermanent suffering not-self",
),
```

- [ ] **Step 9: Add english_hint to "Mind / citta"**

Find the entry with `label="Mind / citta"`. It currently ends with:

```python
    pali="citta mano manopubbaṅgamā manomaya cetovimutti",
),
```

Change to:

```python
    pali="citta mano manopubbaṅgamā manomaya cetovimutti",
    english_hint="mind is the forerunner of all actions with mind as chief mind-made if one speaks or acts with a corrupted mind suffering follows if with a clear mind happiness follows",
),
```

- [ ] **Step 10: Add english_hint to "Defilements / kilesa"**

Find the entry with `label="Defilements / kilesa"`. It currently ends with:

```python
    pali="kilesa lobha dosa moha rāga byāpāda avijjā",
),
```

Change to:

```python
    pali="kilesa lobha dosa moha rāga byāpāda avijjā",
    english_hint="greed hate delusion contaminate the mind unwholesome roots defiled mind blameworthy leads to harm suffering not freed from rebirth",
),
```

- [ ] **Step 11: Add english_hint to "Middle Way"**

Find the entry with `label="Middle Way"`. It currently ends with:

```python
    pali="majjhimā paṭipadā atitta atilīna soṇa vīṇā",
),
```

Change to:

```python
    pali="majjhimā paṭipadā atitta atilīna soṇa vīṇā",
    english_hint="avoiding these two extremes neither given over to sensual pleasure nor to self-mortification the middle path leading to calm direct knowledge awakening nibbana",
),
```

- [ ] **Step 12: Run to verify all 12 english_hint tests pass**

Run: `PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -v -k "lookup_english_anicca or lookup_english_dukkha or lookup_english_nibbana or lookup_english_anatta or lookup_english_no_self or lookup_english_kamma or lookup_english_samadhi or lookup_english_sila or lookup_english_panna or lookup_english_citta or lookup_english_kilesa or lookup_english_middle_way"`

Expected: 12 passed

- [ ] **Step 13: Run full test suite**

Run: `PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -v`

Expected: 35 passed, 0 failed

- [ ] **Step 14: Run broader backend tests to confirm no regressions**

Run: `PYTHONPATH=. python3 -m pytest tests/backend/ -q --ignore=tests/backend/test_e2e_pipeline.py --ignore=tests/backend/test_search_pipeline.py`

(Ignoring e2e and search_pipeline tests that require live Qdrant/LLM connections.)

Expected: all pass

- [ ] **Step 15: Commit**

```bash
git add backend/app/services/pali_dictionary.py tests/backend/test_pali_dictionary.py
git commit -m "feat: add english_hints to 11 pali_dictionary entries for common doctrinal terms"
```
