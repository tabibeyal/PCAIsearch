# Spec: Pali Dictionary — English Hints & Keyword Coverage

**Date:** 2026-05-22
**Status:** Approved

## Problem

Scholars searching the Pali Canon with bare doctrinal terms ("anicca", "nibbāna", "paññā") get degraded results. The embedding model (`paraphrase-multilingual-MiniLM-L12-v2`) does not understand Pali, so the original query vector lands in a meaningless position in embedding space. The LLM expansion (ExpansionPrompt v7, Line 1) compensates on the dense-retrieval side, and BM25 handles exact-match. However, the reranker (ms-marco-MiniLM-L-6-v2) also needs an English passage hint to score retrieved documents correctly — and for most standalone Pali terms, `lookup_english()` currently returns `None`.

## Root Cause

`pali_dictionary.py` contains ~50 entries. Many entries match Pali keywords via `lookup()` but have `english_hint=None`. The `lookup_english()` function returns `None` for these, so the reranker receives no verbatim English signal. Additionally, 4–5 high-frequency standalone Pali terms are absent from keyword lists entirely, causing both `lookup()` and `lookup_english()` to return `None`.

## Scope

Changes are confined entirely to `backend/app/services/pali_dictionary.py`. No architectural changes, no schema changes, no re-indexing required.

## Part 1 — Add `english_hint` to Entries That Lack One

The following entries match on common Pali queries but return `None` from `lookup_english()`. Each needs an `english_hint` written in sutta-translation vocabulary (Thanissaro Bhikkhu style), since documents in the index contain that style of English.

| Entry label | Triggered by | Hint content (sutta-style English) |
|---|---|---|
| Three Marks of Existence | "anicca", "anatta", "three marks" | "form is impermanent feeling is impermanent all fabrications are impermanent subject to change suffering not-self this is not mine I am not this this is not my self" |
| Suffering / dukkha | "dukkha", "stress" | "birth is suffering aging is suffering death is suffering sorrow lamentation pain grief despair not getting what one wants is suffering the five aggregates of clinging are suffering" |
| Ignorance / avijjā | "avijja", "ignorance" | "not knowing suffering not knowing its origin not knowing its cessation not knowing the path with ignorance as condition formations arise" |
| Nibbāna / liberation | "nibbana", "nirvana" | "unborn unbecome unmade unconditioned there would be no escape from what is born become made conditioned deathless cessation unbinding" |
| Not-self / anattā | "anatta", "not-self" | "form is not-self if form were self form would not lead to affliction this is not mine I am not this this is not my self feeling perception fabrications consciousness not-self" |
| Kamma / rebirth | "kamma", "karma" | "beings are owners of their actions heirs of their actions actions are the womb from which they are born whatever actions they do good or bad they will inherit" |
| Concentration / samādhi | "concentration", "samadhi" | "unified mind concentrated one-pointed seclusion rapture pleasure equanimity developed cultivated noble right concentration made much of" |
| Ethical conduct / sīla | "sila", "virtue", "ethical conduct" | "virtue training rule of training restraint refraining abstaining purified upright blameless praised by the wise conduct bodily verbal mental" |
| Wisdom / insight | "wisdom", "insight", "discernment" | "knowing and seeing things as they actually are discernment clear seeing understanding arising and passing away impermanent suffering not-self" |
| Mind / citta | "mind", "mind is the forerunner" | "mind is the forerunner of all actions with mind as chief mind-made if one speaks or acts with a corrupted mind suffering follows if with a clear mind happiness follows" |
| Defilements / kilesa | "kilesa", "greed hate delusion" | "greed hate delusion contaminate the mind unwholesome roots defiled mind blameworthy leads to harm suffering not freed from rebirth" |
| Middle Way | "middle way", "middle path" | "avoiding these two extremes neither given over to sensual pleasure nor to self-mortification the middle path leading to calm direct knowledge awakening nibbana" |

## Part 2 — Add Missing Standalone Keywords

Four high-frequency standalone Pali terms currently return `None` from both `lookup()` and `lookup_english()` because they are absent from keyword lists:

| Term(s) to add | Target entry | Why missing |
|---|---|---|
| `"dukkha"` | Suffering / dukkha | Entry only has English synonyms ("stress", "suffering"); bare Pali form absent |
| `"samadhi"`, `"samādhi"` | Concentration / samādhi | Entry has no Pali keywords at all; only English synonyms |
| `"paññā"`, `"panna"` | Wisdom / insight | Entry only has English synonyms; bare Pali form absent |
| `"sati"` | Mindfulness / satipaṭṭhāna | Entry has "satipaṭṭhāna" but not bare "sati" |
| `"taṇhā"`, `"tanha"` | Three types of craving | Entry has "craving for becoming" etc. but not bare "tanha"/"taṇhā" |
| `"rāga"`, `"raga"` | Defilements / kilesa | Entry only matches "greed hate delusion" in English; bare "raga" absent |

**Keyword regex note:** `_matches()` uses `\b` word-boundary anchors. Python treats non-ASCII characters (ā, ī, ū, ñ, ṭ etc.) as `\W`, so `\bpaññā\b` fails when `paññā` is the full query (trailing boundary fails). The pattern is already established in the file: always pair the diacritical form with an ASCII fallback (e.g., `"tanha"` alongside `"taṇhā"`).

## Success Criteria

After the change:
- `lookup_english("anicca")` returns a non-None string
- `lookup_english("nibbana")` returns a non-None string
- `lookup_english("panna")` returns a non-None string
- `lookup("dukkha")` returns a non-None string
- `lookup("samadhi")` returns a non-None string
- `lookup("sati")` returns a non-None string
- `lookup("tanha")` returns a non-None string
- Existing `lookup()` and `lookup_english()` results for all currently-covered entries are unchanged
- All existing tests pass

## Out of Scope

- Re-indexing Qdrant (not needed)
- Option B (routing Pali variants away from dense retrieval)
- Option C (pre-translating the original query before embedding)
- Adding new entries beyond the 4 keyword additions above
