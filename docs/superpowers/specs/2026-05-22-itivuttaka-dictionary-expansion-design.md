# Spec: Pali Dictionary — Itivuttaka Expansion & Bhikkhu Entry

**Date:** 2026-05-22
**Status:** Approved

## Problem

The Itivuttaka (112 short suttas, prefix `iti`) is heavily indexed in the corpus but its recurring doctrinal vocabulary is underrepresented in `pali_dictionary.py`. Queries about nibbāna elements, conscience/prudence, merit, trainee stage, or escape elements return degraded results because:

1. Those entries don't exist in the dictionary → `lookup()` returns `None` → no Pali term cluster and no english_hint for the reranker.
2. Several existing entries are missing their Pali keyword forms (`appamāda`, `kusala`, `akusala`) and their secondary English synonyms from both translation styles (Thanissaro and Sujato).
3. `bhikkhu` — the single most frequent word in the entire corpus — has no entry, so queries about monastic life, monk roles, or training return no dictionary signal.

## Scope

All changes are confined to `backend/app/services/pali_dictionary.py` and `tests/backend/test_pali_dictionary.py`. No indexing, no pipeline changes, no schema changes.

English hints must use Thanissaro Bhikkhu vocabulary where it does not conflict with the corpus. Because the corpus uses Bhikkhu Sujato's translation ("mendicants"), bhikkhu-related hints include **both** "monk" and "mendicant" so the reranker can match either.

## Part 1 — Six New Entries

### 1. Nibbāna Elements — with/without residue

**Label:** Two elements of Nibbāna  
**Pali cluster:** nibbānadhātu, saupādisesā, anupādisesā, nibbāna element, with residue, without residue  
**Keywords:** `"nibbana element"`, `"nibbanadhatu"`, `"nibbānadhātu"`, `"with residue"`, `"without residue"`, `"extinguishment element"`, `"two elements"`  
**Source sutta:** iti44  
**English hint (Thanissaro/sutta style):** `"two elements of unbinding with residue remaining the faculties still present but all suffering experienced here will fade away without residue remaining at death all that is felt not being relished will grow cold the destruction of passion aversion delusion"`

### 2. Hirī and Ottappa — conscience and prudence

**Label:** Conscience and prudence  
**Pali cluster:** hirī, ottappa, moral shame, moral dread, bright things  
**Keywords:** `"hiri"`, `"hirī"`, `"ottappa"`, `"conscience"`, `"prudence"`, `"moral shame"`, `"moral dread"`, `"two bright things"`, `"bright qualities"`  
**Source sutta:** iti42  
**English hint:** `"conscience and prudence these two bright qualities protect the world conscience shame at doing evil prudence dread of doing evil without these no distinction of mother aunt sister wife of teacher monks mendicants"`

### 3. Three Grounds for Merit

**Label:** Grounds for making merit  
**Pali cluster:** puññakiriyavatthu, giving, virtue, meditation  
**Keywords:** `"grounds for merit"`, `"merit"`, `"making merit"`, `"puññakiriyavatthu"`, `"punnakiriyavatthu"`, `"three grounds"`, `"generosity virtue meditation"`  
**Source sutta:** iti60  
**English hint:** `"three grounds for making merit giving ethical conduct meditation the wise person desiring happiness should train in these works of merit which have great fruit great benefit the wise give generously cultivate virtue develop meditation merit"`

### 4. Trainee / Sekha

**Label:** Trainee / sekha  
**Pali cluster:** sekha, trainee, one in training, stream-enterer to arahant  
**Keywords:** `"sekha"`, `"trainee"`, `"one in training"`, `"learner"`, `"still training"`, `"not yet complete"`  
**Source suttas:** iti16, iti17  
**English hint:** `"a trainee one in higher training who has not yet reached the goal longing for relief from the yoke a monk practicing to eliminate greed hate delusion will not return to this world"`

### 5. Elements of Escape

**Label:** Elements of escape  
**Pali cluster:** nissaraṇadhātu, renunciation, formlessness, cessation  
**Keywords:** `"elements of escape"`, `"nissarana"`, `"nissaraṇa"`, `"escape from sensuality"`, `"escape from form"`, `"renunciation escapes"`, `"formless escapes sensuality"`, `"cessation escapes form"`  
**Source sutta:** iti72  
**English hint:** `"renunciation is the escape from sensuality formlessness is the escape from form cessation is the escape from what is felt as fabricated whatever beings sense some measure of pleasure joy that is the allure the escape is nibbana"`

### 6. Bhikkhu / Monk

**Label:** Bhikkhu / monk  
**Pali cluster:** bhikkhu, bhikkhunī, monk, nun, monastic  
**Keywords:** `"bhikkhu"`, `"bhikkhuni"`, `"bhikkhunī"`, `"monk"`, `"nun"`, `"monastic"`, `"mendicant"`  
**English hint:** `"a monk a mendicant bhikkhu one gone forth from the home life into homelessness training in the higher virtue higher mind higher wisdom practicing the holy life living the celibate life bound for liberation nibbana"`

## Part 2 — Keyword Additions to Three Existing Entries

### Defilements / kilesa

**Add keywords:** `"three roots"`, `"three fires"`, `"fire of greed"`, `"fire of hate"`, `"fire of delusion"`, `"unskillful roots"`, `"akusala"`, `"three unwholesome roots"`  
**Why:** iti93 uses fire metaphor; queries like "fire of greed" and "three roots of evil" land on kilesa entry or nowhere. Bare "akusala" also has no route.

### Heedfulness / appamāda

**Add keywords:** `"appamada"`, `"appamāda"`, `"keen"`, `"prudent"`, `"not negligent"`, `"diligent"`, `"heedless"`, `"negligence"`  
**Why:** "appamada" is the bare Pali form — currently absent. Sujato translates appamāda as "keen"; Thanissaro uses "heedful". Both forms needed.

### Skillful and unskillful

**Add keywords:** `"kusala"`, `"akusala"`, `"good conduct"`, `"bad conduct"`, `"three kinds of conduct"`, `"bodily conduct"`, `"verbal conduct"`, `"mental conduct"`, `"wholesome"`, `"unwholesome"`  
**Why:** iti64/iti65 frame conduct as bodily/verbal/mental. Bare "kusala" and "akusala" are high-frequency query terms with no current route.

## Success Criteria

After the change:

- `lookup("bhikkhu")` returns a non-None string containing "bhikkhu"
- `lookup("hiri")` returns a non-None string containing "hirī"
- `lookup("sekha")` returns a non-None string containing "sekha"
- `lookup("appamada")` returns a non-None string
- `lookup("kusala")` returns a non-None string
- `lookup("akusala")` returns a non-None string
- `lookup_english("bhikkhu")` returns a string containing both "monk" and "mendicant"
- `lookup_english("nibbana element")` returns a non-None string containing "residue"
- `lookup_english("hiri")` returns a non-None string containing "conscience"
- `lookup_english("grounds for merit")` returns a non-None string containing "giving"
- `lookup_english("sekha")` returns a non-None string containing "trainee"
- `lookup_english("elements of escape")` returns a non-None string containing "renunciation"
- All existing 35 tests continue to pass

## Out of Scope

- Adding every Itivuttaka sutta as a separate entry (112 suttas, diminishing returns)
- Changing the translation corpus (Sujato files remain unchanged)
- Re-indexing Qdrant
- Pipeline changes
