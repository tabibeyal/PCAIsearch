# Itivuttaka Dictionary Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 6 new `DictionaryEntry` objects for key Itivuttaka doctrinal topics and a bhikkhu/monk entry, plus expand keywords on 3 existing entries, so the reranker receives verbatim English passage hints for these high-frequency queries.

**Architecture:** All changes are confined to `backend/app/services/pali_dictionary.py` (data only — no function changes) and `tests/backend/test_pali_dictionary.py` (new tests only). TDD order: red tests first, then minimal implementation to pass, then commit. Part 2 (keyword additions to existing entries) goes first, Part 1 (new entries) second.

**Tech Stack:** Python 3, pytest, `re` module (already in use). No new dependencies.

---

### Task 1: Red tests — Part 2 keyword additions to existing entries

**Files:**
- Test: `tests/backend/test_pali_dictionary.py`

- [ ] **Step 1: Append the following red tests to the test file**

Add these tests at the end of `tests/backend/test_pali_dictionary.py`:

```python
# --- Part 2: keyword additions to existing entries ---

def test_lookup_three_fires():
    # kilesa entry gets "three fires"
    result = lookup("three fires")
    assert result is not None
    assert "kilesa" in result


def test_lookup_fire_of_greed():
    # kilesa entry gets "fire of greed"
    result = lookup("fire of greed")
    assert result is not None
    assert "kilesa" in result


def test_lookup_three_roots():
    # kilesa entry gets "three roots"
    result = lookup("three roots")
    assert result is not None
    assert "kilesa" in result


def test_lookup_keen():
    # appamāda entry gets "keen"
    result = lookup("keen")
    assert result is not None
    assert "appamāda" in result


def test_lookup_prudent():
    # appamāda entry gets "prudent"
    result = lookup("prudent")
    assert result is not None
    assert "appamāda" in result


def test_lookup_good_conduct():
    # skillful/unskillful entry gets "good conduct"
    result = lookup("good conduct")
    assert result is not None
    assert "kusala" in result


def test_lookup_bad_conduct():
    # skillful/unskillful entry gets "bad conduct"
    result = lookup("bad conduct")
    assert result is not None
    assert "kusala" in result
```

- [ ] **Step 2: Run the new tests to confirm they all fail**

```
PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -q -k "three_fires or fire_of_greed or three_roots or test_lookup_keen or test_lookup_prudent or good_conduct or bad_conduct"
```

Expected: 7 failures, all `AssertionError` or the result is None.

---

### Task 2: Implement Part 2 keyword additions — make green and commit

**Files:**
- Modify: `backend/app/services/pali_dictionary.py`

- [ ] **Step 1: Add keywords to the Defilements / kilesa entry**

Find the kilesa entry (search for `label="Defilements / kilesa"`). Replace its `keywords` list with:

```python
        keywords=[
            "defilement", "defilements", "kilesa", "mental defilement",
            "unwholesome", "roots of unwholesomeness", "greed hate delusion",
            "lobha dosa moha",
            "raga", "rāga",
            "three roots", "three fires", "fire of greed", "fire of hate", "fire of delusion",
            "unskillful roots", "three unwholesome roots",
        ],
```

- [ ] **Step 2: Add keywords to the Heedfulness / appamāda entry**

Find the appamāda entry (search for `label="Heedfulness / appamāda"`). Replace its `keywords` list with:

```python
        keywords=[
            "heedfulness", "heedful", "heedless", "heedlessness",
            "appamāda", "appamada", "pamāda", "pamada",
            "diligence", "non-negligence", "negligence",
            "accomplish with heedfulness", "strive with heedfulness",
            "last words of the buddha",
            "ardent", "ātāpī", "atapi",
            "alert", "sampajāno", "sampajano",
            "keen", "prudent", "not negligent",
        ],
```

- [ ] **Step 3: Add keywords to the Skillful and unskillful entry**

Find the entry (search for `label="Skillful and unskillful / kusala-akusala"`). Replace its `keywords` list with:

```python
        keywords=[
            "skillful", "unskillful", "kusala", "akusala",
            "what is skillful", "what is unskillful",
            "skillful qualities", "unskillful qualities",
            "skillful action", "unskillful action",
            "wholesome roots", "unwholesome roots",
            "roots of skillfulness", "roots of unskillfulness",
            "non-greed", "non-aversion", "non-delusion",
            "alobha", "adosa", "amoha",
            "good conduct", "bad conduct", "three kinds of conduct",
            "bodily conduct", "verbal conduct", "mental conduct",
            "wholesome", "unwholesome",
        ],
```

- [ ] **Step 4: Run the full test suite and confirm all tests pass**

```
PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -q
```

Expected: all tests pass (35 existing + 7 new = 42 total). If any test fails, check the exact keyword spelling against the query in the test.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pali_dictionary.py tests/backend/test_pali_dictionary.py
git commit -m "feat: expand keywords on kilesa, appamada, and kusala-akusala entries"
```

---

### Task 3: Red tests — Part 1, six new dictionary entries

**Files:**
- Test: `tests/backend/test_pali_dictionary.py`

- [ ] **Step 1: Append the following red tests to the test file**

Add these tests at the end of `tests/backend/test_pali_dictionary.py`:

```python
# --- Part 1: six new Itivuttaka entries ---

def test_lookup_two_nibbana_elements():
    result = lookup("nibbana element")
    assert result is not None
    assert "nibbānadhātu" in result


def test_lookup_english_two_nibbana_elements():
    result = lookup_english("nibbana element")
    assert result is not None
    assert "residue" in result


def test_lookup_hiri():
    result = lookup("hiri")
    assert result is not None
    assert "hirī" in result


def test_lookup_english_hiri():
    result = lookup_english("hiri")
    assert result is not None
    assert "conscience" in result


def test_lookup_grounds_for_merit():
    result = lookup("grounds for merit")
    assert result is not None
    assert "puñña" in result


def test_lookup_english_grounds_for_merit():
    result = lookup_english("grounds for merit")
    assert result is not None
    assert "giving" in result


def test_lookup_sekha():
    result = lookup("sekha")
    assert result is not None
    assert "sekha" in result


def test_lookup_english_sekha():
    result = lookup_english("sekha")
    assert result is not None
    assert "trainee" in result


def test_lookup_elements_of_escape():
    result = lookup("elements of escape")
    assert result is not None
    assert "nissaraṇadhātu" in result


def test_lookup_english_elements_of_escape():
    result = lookup_english("elements of escape")
    assert result is not None
    assert "renunciation" in result


def test_lookup_bhikkhu():
    result = lookup("bhikkhu")
    assert result is not None
    assert "bhikkhu" in result


def test_lookup_english_bhikkhu():
    result = lookup_english("bhikkhu")
    assert result is not None
    assert "monk" in result
    assert "mendicant" in result


def test_lookup_monk():
    # bare "monk" routes to bhikkhu entry
    result = lookup("monk")
    assert result is not None
    assert "bhikkhu" in result
```

- [ ] **Step 2: Run the new tests to confirm they all fail**

```
PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -q -k "nibbana_element or test_lookup_hiri or grounds_for_merit or test_lookup_sekha or elements_of_escape or test_lookup_bhikkhu or test_lookup_monk"
```

Expected: 13 failures. All return `None` (entries don't exist yet).

---

### Task 4: Implement Part 1 — add six new entries, make green, commit

**Files:**
- Modify: `backend/app/services/pali_dictionary.py`

- [ ] **Step 1: Append six new entries inside `_ENTRIES` before its closing bracket**

Find the end of `_ENTRIES` — the last `DictionaryEntry` is the "Food and eating / āhāra" entry ending at line ~789, followed by the closing `]` of the list. Insert the following six entries between the last existing entry's closing `)` comma and that `]`:

```python
    DictionaryEntry(
        label="Two elements of nibbāna",
        keywords=[
            "nibbana element", "nibbāna element", "nibbanadhatu", "nibbānadhātu",
            "with residue", "without residue", "extinguishment element",
            "two elements of unbinding", "two nibbana elements",
            "parinibbana", "parinibbāna",
        ],
        pali="nibbānadhātu saupādisesā anupādisesā nibbāna parinibbāna",
        english_hint="two elements of unbinding with residue remaining the faculties still present but all suffering experienced here will fade away without residue remaining at death all that is felt not being relished will grow cold the destruction of passion aversion delusion",
    ),
    DictionaryEntry(
        label="Conscience and prudence / hirī-ottappa",
        keywords=[
            "hiri", "hirī", "ottappa", "conscience", "moral shame", "moral dread",
            "two bright things", "bright qualities", "prudence",
            "shame at wrongdoing", "fear of wrongdoing",
        ],
        pali="hirī ottappa lajjī lokapāla",
        english_hint="conscience and prudence these two bright qualities protect the world conscience shame at doing evil prudence dread of doing evil without these no distinction of mother aunt sister wife of teacher monks mendicants",
    ),
    DictionaryEntry(
        label="Three grounds for making merit / puññakiriyavatthu",
        keywords=[
            "grounds for merit", "puññakiriyavatthu", "punnakiriyavatthu",
            "three grounds", "making merit", "merit making",
            "generosity virtue meditation merit",
        ],
        pali="puññakiriyavatthu dāna sīla bhāvanā cāga puñña",
        english_hint="three grounds for making merit giving ethical conduct meditation the wise person desiring happiness should train in these works of merit which have great fruit great benefit the wise give generously cultivate virtue develop meditation merit",
    ),
    DictionaryEntry(
        label="Trainee / sekha",
        keywords=[
            "sekha", "trainee", "one in training", "learner",
            "still training", "not yet complete", "in higher training",
        ],
        pali="sekha sikkhā adhisīla adhicitta adhipaññā sotāpanna",
        english_hint="a trainee one in higher training who has not yet reached the goal longing for relief from the yoke a monk practicing to eliminate greed hate delusion will not return to this world",
    ),
    DictionaryEntry(
        label="Elements of escape / nissaraṇadhātu",
        keywords=[
            "elements of escape", "nissarana", "nissaraṇa", "nissaraṇadhātu",
            "escape from sensuality", "escape from form", "renunciation escapes",
            "formless escapes sensuality", "cessation escapes form",
        ],
        pali="nissaraṇadhātu nekkhamma abyāpajjha nirodha nibbāna",
        english_hint="renunciation is the escape from sensuality formlessness is the escape from form cessation is the escape from what is felt as fabricated whatever beings sense some measure of pleasure joy that is the allure the escape is nibbana",
    ),
    DictionaryEntry(
        label="Bhikkhu / monk",
        keywords=[
            "bhikkhu", "bhikkhuni", "bhikkhunī", "monk", "nun", "monastic",
            "mendicant", "gone forth", "homeless life", "ordained",
        ],
        pali="bhikkhu bhikkhunī pabbajita sāmaṇera brahmacariya sīla sikkhā",
        english_hint="a monk a mendicant bhikkhu one gone forth from the home life into homelessness training in the higher virtue higher mind higher wisdom practicing the holy life living the celibate life bound for liberation nibbana",
    ),
```

- [ ] **Step 2: Run the full test suite and confirm all tests pass**

```
PYTHONPATH=. python3 -m pytest tests/backend/test_pali_dictionary.py -q
```

Expected: all 55 tests pass (42 from previous task + 13 new). If any assertion fails, check that the pali string and english_hint in the entry contain the exact substring asserted in the test.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/pali_dictionary.py tests/backend/test_pali_dictionary.py
git commit -m "feat: add six new Itivuttaka entries and bhikkhu entry to pali dictionary"
```

---

### Task 5: Final full-suite check and push

**Files:** none (verification only)

- [ ] **Step 1: Run the complete backend test suite**

```
PYTHONPATH=. python3 -m pytest tests/backend/ -q
```

Expected: all tests pass. If `test_reranking.py` shows pre-existing failures (unrelated to this work), confirm they existed before Task 1 by checking git log — if so, they are not regressions.

- [ ] **Step 2: Push**

```bash
git push
```
