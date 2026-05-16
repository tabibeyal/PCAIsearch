# Pāḷi Term Dictionary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a curated Pāḷi term dictionary that injects a deterministic 3rd expansion variant into the query expansion pipeline, improving recall for queries where the LLM generates hallucinated Pāḷi.

**Architecture:** A new `pali_dictionary.py` module holds ~50–80 entries (keywords → Pāḷi cluster). `lookup(query)` is called inside `expand_query()` after the LLM call; if a match is found, the Pāḷi string is appended as a 3rd variant. All downstream code (BM25 × N, dense × N, RRF fusion) already loops over variable-length variant lists.

**Tech Stack:** Python stdlib only (`dataclasses`, `typing`). No new dependencies.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/app/services/pali_dictionary.py` | Dictionary entries + `lookup()` |
| Create | `tests/backend/test_pali_dictionary.py` | Unit tests for `lookup()` |
| Modify | `backend/app/services/search_pipeline.py` lines 159–177 | Import + call `lookup()` in `expand_query()` |
| Modify | `tests/backend/test_search_pipeline.py` | Integration tests for 3-variant expansion |

---

## Task 1: Create `pali_dictionary.py` with entries and `lookup()`

**Files:**
- Create: `backend/app/services/pali_dictionary.py`

- [ ] **Step 1: Write the failing test**

Create `tests/backend/test_pali_dictionary.py`:

```python
from backend.app.services.pali_dictionary import lookup


def test_lookup_dependent_origination():
    result = lookup("how does ignorance cause suffering step by step")
    assert result is not None
    assert "paṭicca-samuppāda" in result
    assert "avijjā" in result


def test_lookup_kalama_sutta():
    result = lookup("how do you know whether a religious teaching is worth following")
    assert result is not None
    assert "kālāmā" in result


def test_lookup_five_aggregates():
    result = lookup("are the five aggregates permanent or do they lack a self")
    assert result is not None
    assert "khandha" in result
    assert "anattā" in result


def test_lookup_saw_simile():
    result = lookup("should a monk feel anger if attacked with a saw")
    assert result is not None
    assert "kakacūpama" in result


def test_lookup_parents_family():
    result = lookup("how should one treat parents family and friends")
    assert result is not None
    assert "sigālovāda" in result


def test_lookup_lying_precept():
    result = lookup("what is the one precept you should never break")
    assert result is not None
    assert "musāvādā" in result


def test_lookup_case_insensitive():
    lower = lookup("loving kindness meditation")
    upper = lookup("LOVING KINDNESS MEDITATION")
    assert lower is not None
    assert lower == upper


def test_lookup_multi_keyword_fires_on_any():
    result = lookup("eightfold path")
    assert result is not None
    assert "sammā-diṭṭhi" in result

    result2 = lookup("right view and right intention")
    assert result2 is not None
    assert "sammā-diṭṭhi" in result2


def test_lookup_unknown_returns_none():
    assert lookup("what is a good recipe for bread") is None
    assert lookup("how do I exit vim") is None


def test_lookup_returns_string():
    result = lookup("four noble truths")
    assert isinstance(result, str)
    assert len(result) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_pali_dictionary.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `pali_dictionary` does not exist yet.

- [ ] **Step 3: Write `pali_dictionary.py`**

Create `backend/app/services/pali_dictionary.py`:

```python
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DictionaryEntry:
    label: str
    keywords: List[str]
    pali: str


_ENTRIES: List[DictionaryEntry] = [
    # ── Four Noble Truths ────────────────────────────────────────────────────
    DictionaryEntry(
        label="Four Noble Truths",
        keywords=["four noble truths", "noble truth", "truth of suffering", "four truths"],
        pali="cattāri ariyasaccāni dukkha samudaya nirodha magga",
    ),
    DictionaryEntry(
        label="Suffering / dukkha",
        keywords=["suffering", "unsatisfactoriness", "cause of suffering", "origin of suffering"],
        pali="dukkha samudaya taṇhā upādāna bhava",
    ),
    # ── Dependent Origination ────────────────────────────────────────────────
    DictionaryEntry(
        label="Dependent Origination (full chain)",
        keywords=[
            "dependent origination", "dependent arising", "conditioned arising",
            "how does ignorance cause", "ignorance cause suffering",
            "twelve links", "12 links", "chain of causation",
            "interdependent arising", "step by step suffering",
            "deepest origin", "root cause of suffering", "fundamental cause",
        ],
        pali="paṭicca-samuppāda avijjā saṅkhārā viññāṇa nāmarūpa salāyatana phassa vedanā taṇhā upādāna bhava jāti jarāmaraṇa",
    ),
    DictionaryEntry(
        label="Ignorance / avijjā",
        keywords=["ignorance", "not knowing", "fundamental ignorance", "avijja"],
        pali="avijjā vijjā paṭicca-samuppāda mūla",
    ),
    # ── Eightfold Path ───────────────────────────────────────────────────────
    DictionaryEntry(
        label="Noble Eightfold Path",
        keywords=[
            "eightfold path", "eight fold path", "noble eightfold",
            "path factors", "right view", "right intention", "right speech",
            "right action", "right livelihood", "right effort",
            "right mindfulness", "right concentration",
        ],
        pali="ariyo aṭṭhaṅgiko maggo sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta sammā-ājīva sammā-vāyāma sammā-sati sammā-samādhi",
    ),
    # ── Five Aggregates ──────────────────────────────────────────────────────
    DictionaryEntry(
        label="Five Aggregates",
        keywords=[
            "five aggregates", "five skandhas", "aggregates of clinging",
            "form feeling perception", "aggregates permanent", "lack a self",
            "khandha", "self in the aggregates", "no self in aggregates",
            "are the aggregates",
        ],
        pali="khandha rūpa vedanā saññā saṅkhārā viññāṇa anicca dukkha anattā",
    ),
    # ── Three Marks of Existence ─────────────────────────────────────────────
    DictionaryEntry(
        label="Three Marks of Existence",
        keywords=[
            "impermanent", "impermanence", "three marks", "anicca",
            "not-self", "no self", "anatta", "three characteristics",
            "unsatisfactory nature",
        ],
        pali="tilakkhaṇa anicca dukkha anattā sabbe saṅkhārā vipariṇāma",
    ),
    # ── Precepts ─────────────────────────────────────────────────────────────
    DictionaryEntry(
        label="Five Precepts",
        keywords=[
            "five precepts", "ethical training", "moral training",
            "precepts householder", "lay precepts", "undertake training",
        ],
        pali="pañcasīla pāṇātipātā adinnādānā kāmesumicchācārā musāvādā surāmeraya sīla",
    ),
    DictionaryEntry(
        label="Precept of truthfulness / lying",
        keywords=[
            "lying", "false speech", "telling the truth",
            "precept never break", "one precept", "truth telling",
            "honesty", "avoid lying", "speak truth",
        ],
        pali="musāvādā sacca ambalatthika-rāhulovāda sīla sammā-vācā",
    ),
    DictionaryEntry(
        label="Precept of non-killing",
        keywords=[
            "killing", "not killing", "first precept", "taking life",
            "ahimsa", "non-violence", "harm living beings", "abstain from killing",
        ],
        pali="pāṇātipātā ahiṃsā pāṇātipātā-veramaṇī sīla",
    ),
    DictionaryEntry(
        label="Precept of non-stealing",
        keywords=[
            "stealing", "not stealing", "taking what is not given",
            "second precept", "property theft", "refrain from stealing",
        ],
        pali="adinnādānā adinnadāna sīla",
    ),
    DictionaryEntry(
        label="Precept of sexual misconduct",
        keywords=[
            "sexual misconduct", "third precept", "sensual misconduct",
            "refrain from sexual misconduct", "kamesu micchacara",
        ],
        pali="kāmesumicchācārā sīla brahmacariya",
    ),
    DictionaryEntry(
        label="Precept of intoxicants",
        keywords=[
            "intoxicants", "alcohol", "fifth precept", "drink",
            "refrain from intoxicants", "surameraya",
        ],
        pali="surāmeraya majja pamādaṭṭhāna sīla",
    ),
    # ── Kālāma / Epistemology ────────────────────────────────────────────────
    DictionaryEntry(
        label="Kālāma Sutta / epistemology",
        keywords=[
            "kālāma", "kalama", "how to know", "whether a teaching is worth",
            "test a teaching", "religious teaching worth following",
            "don't follow tradition", "anussava", "not by hearsay",
            "how do you judge", "criteria for truth", "verify teaching",
        ],
        pali="kālāmā anussava parampara itikirā piṭakasampadā takkahetu nayahetu",
    ),
    # ── Jhāna / Meditation states ────────────────────────────────────────────
    DictionaryEntry(
        label="Jhāna / absorption",
        keywords=[
            "jhana", "jhāna", "meditative absorption", "four jhanas",
            "first jhana", "second jhana", "third jhana", "fourth jhana",
            "enter jhana", "meditative states",
        ],
        pali="jhāna samādhi vitakka vicāra pīti sukha ekaggatā upekkhā",
    ),
    DictionaryEntry(
        label="Concentration / samādhi",
        keywords=[
            "concentration", "one-pointedness", "mental unification",
            "stillness of mind", "calm abiding", "serenity",
            "unified mind", "collected mind",
        ],
        pali="samādhi samatha cetaso ekodibhāva",
    ),
    DictionaryEntry(
        label="Mindfulness / satipaṭṭhāna",
        keywords=[
            "mindfulness", "four foundations of mindfulness", "satipatthana",
            "contemplation of body", "mindfulness of breathing",
            "breath awareness", "anapanasati", "ānāpānasati",
            "body mind contemplation",
        ],
        pali="satipaṭṭhāna kāyānupassanā vedanānupassanā cittānupassanā dhammānupassanā ānāpānasati",
    ),
    # ── Brahmavihārās ────────────────────────────────────────────────────────
    DictionaryEntry(
        label="Brahmavihārās / four immeasurables",
        keywords=[
            "loving kindness", "lovingkindness", "metta", "compassion",
            "sympathetic joy", "equanimity", "four immeasurables",
            "brahmaviharas", "divine abiding", "radiate goodwill",
            "boundless heart", "immeasurable mind",
        ],
        pali="brahmavihāra mettā karuṇā muditā upekkhā pharaṇa sattā",
    ),
    DictionaryEntry(
        label="Mettā / loving-kindness practice",
        keywords=["metta meditation", "loving kindness meditation", "goodwill to all"],
        pali="mettā sattā sukhī hontu brahmavihāra pharaṇa",
    ),
    # ── Similes ──────────────────────────────────────────────────────────────
    DictionaryEntry(
        label="Saw simile / patience under abuse",
        keywords=[
            "saw", "anger", "attacked with a saw", "sawn limb by limb",
            "patience under attack", "if someone attacks", "should a monk feel anger",
            "monk attacked", "abuse patience", "axe simile",
        ],
        pali="kakacūpama khanti anāghāta abyāpajjha mettā",
    ),
    DictionaryEntry(
        label="Raft simile",
        keywords=[
            "raft", "raft simile", "cross to the other shore",
            "dhamma like a raft", "leave the raft behind",
        ],
        pali="kullūpama dhamma vinaya ogha tīra",
    ),
    DictionaryEntry(
        label="Poison arrow simile",
        keywords=[
            "poison arrow", "poisoned arrow", "arrow in the flesh",
            "metaphysical questions", "undeclared questions", "unanswered",
        ],
        pali="sallena āhata avyākata abyākata diṭṭhi",
    ),
    # ── Spiritual friendship ─────────────────────────────────────────────────
    DictionaryEntry(
        label="Spiritual friendship",
        keywords=[
            "spiritual friend", "good friend", "kalyanamitra", "admirable friend",
            "whole of the holy life", "half the holy life", "noble friend",
            "spiritual companionship",
        ],
        pali="kalyāṇamittā kalyāṇasahāya kalyāṇasampavaṅka brahmacariya",
    ),
    # ── Middle Way ───────────────────────────────────────────────────────────
    DictionaryEntry(
        label="Middle Way",
        keywords=[
            "middle way", "middle path", "neither too tight nor too loose",
            "lute strings", "extreme", "asceticism and sensual pleasure",
            "avoid extremes", "moderate path",
        ],
        pali="majjhimā paṭipadā atitta atilīna soṇa vīṇā",
    ),
    # ── First Sermon ─────────────────────────────────────────────────────────
    DictionaryEntry(
        label="First Sermon / Dhammacakkappavattana",
        keywords=[
            "first discourse", "first sermon", "setting in motion",
            "wheel of dhamma", "wheel of the dhamma", "deer park",
            "isipatana", "five ascetics", "first teaching",
        ],
        pali="dhammacakkappavattana isipatana migadāya pañcavaggiyā",
    ),
    # ── Householder ethics / Sigālovāda ─────────────────────────────────────
    DictionaryEntry(
        label="Sigālovāda / householder ethics",
        keywords=[
            "parents", "treat parents", "honour parents",
            "family", "husband wife", "sigala", "sigalovada",
            "householder ethics", "how should one treat",
            "obligations to family", "respect parents", "six directions",
        ],
        pali="sigālovāda mātāpitaro disa ācariya putta dāra mitta",
    ),
    # ── Death / recollection ─────────────────────────────────────────────────
    DictionaryEntry(
        label="Death / maraṇānussati",
        keywords=[
            "death", "dying", "mortality", "old age death",
            "born to die", "recollection of death", "maranasati",
            "contemplation of death",
        ],
        pali="maraṇa jarā jāti maraṇānussati anicca",
    ),
    # ── Nibbāna / liberation ─────────────────────────────────────────────────
    DictionaryEntry(
        label="Nibbāna / liberation",
        keywords=[
            "nibbana", "nirvana", "awakening", "enlightenment",
            "freedom from suffering", "cessation", "unbinding",
            "liberation", "deathless", "unconditioned",
        ],
        pali="nibbāna vimutti vimokkha sacchikiriyā asaṅkhata",
    ),
    DictionaryEntry(
        label="Wisdom / insight",
        keywords=[
            "wisdom", "insight", "discernment", "clear seeing",
            "true knowledge", "seeing things as they are",
        ],
        pali="paññā vijjā ñāṇa dassana yathābhūta",
    ),
    # ── Kamma / rebirth ──────────────────────────────────────────────────────
    DictionaryEntry(
        label="Kamma / rebirth",
        keywords=[
            "rebirth", "reincarnation", "kamma", "karma",
            "action and result", "intention", "future lives", "next life",
            "volitional action",
        ],
        pali="kamma cetanā vipāka punabbhava saṃsāra",
    ),
    # ── Three Refuges ────────────────────────────────────────────────────────
    DictionaryEntry(
        label="Three Jewels / Refuges",
        keywords=[
            "three jewels", "three refuges", "buddha dharma sangha",
            "take refuge", "going for refuge", "tiratana",
            "refuge in the buddha",
        ],
        pali="tiratana buddha dhamma saṅgha saraṇa",
    ),
    # ── Stages of awakening ──────────────────────────────────────────────────
    DictionaryEntry(
        label="Stages of awakening",
        keywords=[
            "stream entry", "stream-entry", "once returner",
            "non-returner", "arahant", "stages of awakening",
            "four stages", "sotapanna", "sakadagami", "anagami",
            "stream enterer",
        ],
        pali="sotāpanna sakadāgāmī anāgāmī arahant ariya magga phala",
    ),
    # ── Fetters / defilements ────────────────────────────────────────────────
    DictionaryEntry(
        label="Fetters / ten fetters",
        keywords=[
            "fetter", "ten fetters", "mental fetters", "bonds",
            "what binds us", "ten bonds", "overcome fetters",
        ],
        pali="saṃyojana sakkāyadiṭṭhi vicikicchā sīlabbataparāmāsa kāmarāga paṭigha",
    ),
    DictionaryEntry(
        label="Five hindrances",
        keywords=[
            "five hindrances", "mental hindrances", "hindrance", "nīvaraṇa",
            "sloth torpor", "restlessness worry", "sensual desire",
            "ill will", "doubt as hindrance",
        ],
        pali="nīvaraṇa kāmacchanda vyāpāda thīnamiddha uddhacca-kukkucca vicikicchā",
    ),
    DictionaryEntry(
        label="Defilements / kilesa",
        keywords=[
            "defilement", "defilements", "kilesa", "mental defilement",
            "unwholesome", "roots of unwholesomeness", "greed hate delusion",
            "lobha dosa moha",
        ],
        pali="kilesa lobha dosa moha rāga byāpāda avijjā",
    ),
    # ── Sense restraint ──────────────────────────────────────────────────────
    DictionaryEntry(
        label="Sense restraint",
        keywords=[
            "sense restraint", "guarding sense doors", "sense control",
            "restrain senses", "eye ear nose tongue body mind",
            "guard the senses", "sense faculties",
        ],
        pali="indriyasaṃvara cakkhu sota ghāna jivhā kāya mano",
    ),
    # ── Vipassanā / insight meditation ───────────────────────────────────────
    DictionaryEntry(
        label="Vipassanā / insight",
        keywords=[
            "vipassana", "vipassanā", "insight meditation",
            "insight into impermanence", "dry insight", "bare insight",
        ],
        pali="vipassanā aniccānupassanā dukkhānupassanā anattānupassanā",
    ),
    # ── Anattā / not-self ────────────────────────────────────────────────────
    DictionaryEntry(
        label="Not-self / anattā",
        keywords=[
            "not self", "not-self", "no self", "anatta", "anattā",
            "what is the self", "is there a self", "self and non-self",
        ],
        pali="anattā sabbe dhammā anattā khandha ahaṃkāra",
    ),
    # ── Dependent Origination (cessation side) ───────────────────────────────
    DictionaryEntry(
        label="Cessation of dependent origination",
        keywords=[
            "cessation of suffering", "end of suffering", "how suffering ends",
            "nirodha", "cessation of dependent origination",
        ],
        pali="nirodha paṭicca-samuppāda-nirodha taṇhā-nirodha nibbāna",
    ),
    # ── Effort / energy ──────────────────────────────────────────────────────
    DictionaryEntry(
        label="Right effort / four great efforts",
        keywords=[
            "right effort", "four great efforts", "four right efforts",
            "abandon unwholesome", "cultivate wholesome", "viriya",
            "energy in practice",
        ],
        pali="sammappadhāna viriya āraddhaviriya padhāna",
    ),
    # ── Sīla / ethics ────────────────────────────────────────────────────────
    DictionaryEntry(
        label="Ethical conduct / sīla",
        keywords=[
            "ethical conduct", "sila", "moral conduct", "virtue",
            "training in ethics", "ethical behaviour",
        ],
        pali="sīla pārisuddhisīla ājīvapārisuddhisīla",
    ),
    # ── Saṅgha / monastic ────────────────────────────────────────────────────
    DictionaryEntry(
        label="Monastic rules / Vinaya",
        keywords=[
            "monk rules", "monastic discipline", "vinaya", "monks and nuns",
            "rules of training", "patimokkha", "monastic code",
            "monks precepts", "bhikkhu rules",
        ],
        pali="vinaya pātimokkha bhikkhu bhikkhunī sikkhāpada",
    ),
    DictionaryEntry(
        label="Saṅgha / community",
        keywords=[
            "community of monks", "sangha", "saṅgha", "monastic community",
            "fourfold sangha", "bhikkhu sangha",
        ],
        pali="saṅgha bhikkhu bhikkhunī upāsaka upāsikā cātuddisa",
    ),
    # ── Food / eating ────────────────────────────────────────────────────────
    DictionaryEntry(
        label="Four nutriments",
        keywords=[
            "four nutriments", "four foods", "nutriment", "food for consciousness",
            "contact as nutriment", "mental volition as nutriment",
        ],
        pali="āhāra kabaḷīkāra phassāhāra manosañcetanāhāra viññāṇāhāra",
    ),
    # ── Cosmology / realms ───────────────────────────────────────────────────
    DictionaryEntry(
        label="Realms of existence",
        keywords=[
            "realms", "six realms", "heavenly realm", "hell realm",
            "deva", "brahma", "realm of beings", "planes of existence",
        ],
        pali="loka sugati duggati deva brahmaloka niraya tiracchāna",
    ),
    # ── Recollections / anussati ─────────────────────────────────────────────
    DictionaryEntry(
        label="Six recollections",
        keywords=[
            "recollection", "six recollections", "recollection of the buddha",
            "recollection of dhamma", "recollection of sangha",
            "anussati", "buddhānussati",
        ],
        pali="anussati buddhānussati dhammānussati saṅghānussati sīlānussati cāgānussati devatānussati",
    ),
    # ── Doubt / faith ────────────────────────────────────────────────────────
    DictionaryEntry(
        label="Faith / saddhā",
        keywords=[
            "faith", "confidence", "trust in the dhamma",
            "faith in the buddha", "saddhā", "verified confidence",
        ],
        pali="saddhā saddahati aveccappasāda",
    ),
    # ── Impermanence of conditioned things ───────────────────────────────────
    DictionaryEntry(
        label="Conditioned things / saṅkhārā",
        keywords=[
            "conditioned things", "conditioned phenomena", "formations",
            "mental formations", "sankharas", "fabrications",
        ],
        pali="saṅkhārā sabbe saṅkhārā aniccā paṭicca-samuppāda",
    ),
    # ── Citta / mind ─────────────────────────────────────────────────────────
    DictionaryEntry(
        label="Mind / citta",
        keywords=[
            "mind", "purification of mind", "training the mind",
            "taming the mind", "mind is the forerunner", "manopubbaṅgamā",
        ],
        pali="citta mano manopubbaṅgamā manomaya cetovimutti",
    ),
    # ── Loving-kindness (Mettāsutta) ─────────────────────────────────────────
    DictionaryEntry(
        label="Mettāsutta",
        keywords=[
            "metta sutta", "mettasutta", "karaṇīya", "loving-kindness sutta",
            "as a mother guards her only child",
        ],
        pali="karaṇīyamettā mātā yathā niyaṃ puttaṃ āyusā ekaputtamanurakkhe",
    ),
    # ── Aggregates - feeling tone ─────────────────────────────────────────────
    DictionaryEntry(
        label="Feeling tone / vedanā",
        keywords=[
            "feeling tone", "vedana", "pleasant feeling", "painful feeling",
            "neutral feeling", "three feelings", "types of feeling",
        ],
        pali="vedanā sukha dukkha adukkhamasukha",
    ),
]


def lookup(query: str) -> Optional[str]:
    q = query.lower()
    for entry in _ENTRIES:
        if any(kw in q for kw in entry.keywords):
            return entry.pali
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_pali_dictionary.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pali_dictionary.py tests/backend/test_pali_dictionary.py
git commit -m "feat: add curated Pāḷi term dictionary with lookup() for deterministic expansion"
```

---

## Task 2: Integrate `lookup()` into `expand_query()`

**Files:**
- Modify: `backend/app/services/search_pipeline.py` — import `lookup`, call it after LLM variants
- Modify: `tests/backend/test_search_pipeline.py` — add two integration tests

- [ ] **Step 1: Write the failing integration tests**

Add to the bottom of `tests/backend/test_search_pipeline.py`:

```python
@pytest.mark.asyncio
async def test_expand_query_appends_dictionary_hit():
    """When lookup() matches, expand_query returns 3 variants with the Pāḷi string last."""
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()

    # Simulate LLM returning 2 lines
    async def fake_create(**kwargs):
        from types import SimpleNamespace
        msg = SimpleNamespace(content="english vocab line\npali line from llm")
        choice = SimpleNamespace(message=msg)
        return SimpleNamespace(choices=[choice])

    pipeline.llm.chat.completions.create = fake_create

    with patch("backend.app.services.search_pipeline.lookup", return_value="avijjā paṭicca-samuppāda") as mock_lookup:
        result = await pipeline.expand_query("how does ignorance cause suffering")

    mock_lookup.assert_called_once_with("how does ignorance cause suffering")
    assert result[-1] == "avijjā paṭicca-samuppāda"
    assert len(result) == 4  # original + 2 LLM lines + 1 dict hit


@pytest.mark.asyncio
async def test_expand_query_no_dictionary_hit_unchanged():
    """When lookup() returns None, expand_query returns the normal 3 variants."""
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()

    async def fake_create(**kwargs):
        from types import SimpleNamespace
        msg = SimpleNamespace(content="english vocab line\npali line from llm")
        choice = SimpleNamespace(message=msg)
        return SimpleNamespace(choices=[choice])

    pipeline.llm.chat.completions.create = fake_create

    with patch("backend.app.services.search_pipeline.lookup", return_value=None):
        result = await pipeline.expand_query("what is a good recipe for bread")

    assert len(result) == 3  # original + 2 LLM lines, no dict hit
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_search_pipeline.py::test_expand_query_appends_dictionary_hit tests/backend/test_search_pipeline.py::test_expand_query_no_dictionary_hit_unchanged -v
```

Expected: FAIL — `lookup` not yet imported in `search_pipeline.py`.

- [ ] **Step 3: Add the integration to `search_pipeline.py`**

At the top of `backend/app/services/search_pipeline.py`, add the import after the existing service imports:

```python
from backend.app.services.pali_dictionary import lookup
```

Then in `expand_query()`, replace:

```python
        return variants[:3]
```

with:

```python
        variants = variants[:3]
        pali_hit = lookup(query)
        if pali_hit:
            variants.append(pali_hit)
        return variants
```

The full updated `expand_query()` method looks like this:

```python
    async def expand_query(self, query: str) -> List[str]:
        prompt = self.expansion_prompt.get_prompt()
        message = await self.llm.chat.completions.create(
            model=self.expansion_model,
            max_tokens=256,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
        )
        raw = _strip_thinking(message.choices[0].message.content)
        extras = [line.strip() for line in raw.splitlines() if line.strip()]
        seen: set = {query}
        variants = [query]
        for v in extras:
            if v not in seen:
                seen.add(v)
                variants.append(v)
        variants = variants[:3]
        pali_hit = lookup(query)
        if pali_hit:
            variants.append(pali_hit)
        return variants
```

- [ ] **Step 4: Run the new integration tests**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_search_pipeline.py::test_expand_query_appends_dictionary_hit tests/backend/test_search_pipeline.py::test_expand_query_no_dictionary_hit_unchanged -v
```

Expected: both PASS.

- [ ] **Step 5: Run the full test suite**

```bash
PYTHONPATH=. python -m pytest tests/backend/ -q --ignore=tests/backend/test_e2e_pipeline.py
```

Expected: ≥ 118 passed, same 6 pre-existing errors in `test_api.py` (missing `NVIDIA_API_KEY` — unchanged).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/search_pipeline.py tests/backend/test_search_pipeline.py
git commit -m "feat: inject Pāḷi dictionary as deterministic 3rd expansion variant in expand_query"
```

---

## Task 3: Benchmark validation

**Files:**
- Run only: `tests/backend/retrieval_benchmark.py`

- [ ] **Step 1: Run the benchmark**

```bash
PYTHONPATH=. python tests/backend/retrieval_benchmark.py --with-bm25 --with-expansion
```

This requires `NVIDIA_API_KEY` set in the environment and a running Qdrant instance. It takes several minutes.

- [ ] **Step 2: Verify results**

Check the output against all three criteria:

| Criterion | Target | Pass? |
|-----------|--------|-------|
| Overall recall@10 | ≥ 53% (8/15) | |
| SN 12.1 or AN 3.65 newly retrieved | at least one | |
| MN 61 not further regressed | still present or no worse | |

- [ ] **Step 3: Update HANDOFF.md**

Add a row to the recall scoreboard in `HANDOFF.md` with the new result. Example row:

```
| Expansion + BM25 + Pāḷi dict | X/5 | X/5 | X/5 | X/15 (X%) |
```

Update the "Open issues" section to reflect which hard misses remain.

- [ ] **Step 4: Commit**

```bash
git add HANDOFF.md
git commit -m "docs: update HANDOFF with Pāḷi dictionary benchmark results"
```
