# Vinaya source material on dhammatalks.org

Research for [#180](https://github.com/tabibeyal/PCAIsearch/issues/180), ticket of the map
[Bring the Vinaya into the corpus](https://github.com/tabibeyal/PCAIsearch/issues/179).
Surveyed 2026-09-16. This report decides nothing — #181 chooses the source.

## Summary of findings

1. **The Vinaya Piṭaka itself is only available in part.** Ṭhānissaro's site publishes the
   **Mahāvagga** (10 of the 22 Khandhakas). The Cullavagga, the Suttavibhaṅga and the Parivāra
   have no canonical translation on the site.
2. **Only the Mahāvagga carries Pāḷi**, and it is sentence-aligned — 9,463 Pāḷi/English pairs.
3. **The Mahāvagga is HTML-only.** No epub, no PDF. The existing fetch path reads one epub, so
   the Mahāvagga needs a new extraction path, not an extension of the current one.
4. **The Buddhist Monastic Code is an epub** with the same flat `Section00NN.html` shape as
   `SuttaPitaka_251113.epub`, and it carries per-rule HTML anchors (`Pc41`, `Pr1`, …) that are
   directly usable as citation IDs. But it is Ṭhānissaro's *explanation* of the rules, not a
   canonical translation, and it is English-only.
5. **Licence is a non-issue.** Every item is CC BY-NC 4.0 — the same licence as this repo.
   No share-alike clause anywhere, unlike SuttaCentral's CC BY-NC-SA 4.0.
6. **Size is material.** The Vinaya candidates add roughly 630,000 English words to a corpus
   that holds about 1,045,000 today — a ~60% increase.

## Inventory

| Item | URL | Format | Pāḷi? | English words | Revision |
|---|---|---|---|---|---|
| Buddhist Monastic Code Vols I & II | `/Archive/Writings/Ebooks/BuddhistMonasticCode_251013.epub` (2.4 MB) | epub, azw3, kepub, PDF (`_251113.pdf`, 11.9 MB), HTML | No (Pāḷi terms only) | 473,012 | rev. 2025-09-10 |
| The Mahāvagga | `/vinaya/Mv/MvI.html` … `MvX.html` | HTML only | **Yes, sentence-aligned** | ~150,000 (of 301,591 total) | none stated |
| Bhikkhu Pāṭimokkha | `/vinaya/bhikkhu-pati.html` | HTML only | No | 11,215 | none stated |
| Bhikkhunī Pāṭimokkha | `/vinaya/bhikkhuni-pati.html` | HTML only | No | 14,631 | none stated |
| The Question of Bhikkhunī Ordination | `/books/QuestionofBhikkhuniOrdination/` | HTML + ebook formats | No | not counted (essays) | rev. 2021-12-17 |
| Stored-up Food (Khematto Bhikkhu) | `/vinaya/StoredUpFood.html` | HTML | Yes, in quotations | not counted (essay) | rev. 2017-10-04 |

Ebook index: `/ebook_index.html`. Essays index: `/vinaya_essays_index.html`.

## Identifier schemes

Three different schemes, none of which matches the pipeline's `PREFIX + number` /
`PREFIX + chapter.number` convention.

**Buddhist Monastic Code** — HTML anchors per rule inside each epub section, e.g.
`Section0020.html` contains `Pc_ChFive`, then `Pc41` … `Pc50`, under an `h2` per rule number.
Rule classes seen: `Pr` (pārājika), `Sg` (saṅghādisesa), `NP` (nissaggiya pācittiya),
`Pc` (pācittiya), `Pd` (pāṭidesanīya), `Sk` (sekhiya), `Ay` (adhikaraṇa-samatha), `Aniy`.
Volume II (Khandhaka chapters) begins at `Section0033.html`.

**Mahāvagga** — two parallel schemes in the same page. Section headings carry Burmese-edition
anchors (`id="burmese1"`, `burmese2`, …) and PTS page anchors (`id="pts8_1"`). The citation
string itself is embedded in the Pāḷi text as a bracketed prefix: `(Mv.I.1.2)` — book, chapter
(Roman), section, paragraph. 563 anchors in chapter I alone.

**Pāṭimokkha pages** — anchors `pr`, `pr-1`, `pr-2`, … one per rule, grouped by rule class.

## Mahāvagga markup detail

Each chapter is a single large HTML page (chapter I is 857 KB). The body is a long run of
paired elements: `<span class="left">` holds Pāḷi, `<span class="right">` holds the English for
the same sentence. Counts are exactly equal in every chapter, so the pairing is reliable.

Example (chapter I, first pair):

- left: `[1] Tena samayena buddho bhagavā uruvelāyaṁ viharati najjā nerañjarāya tīre bodhirukkhamūle paṭhamābhisambuddho.`
- right: `Now on that occasion the Buddha, the Blessed One, was staying at Uruvelā on the bank of the Nerañjarā River at the root of the Bodhi tree…`

Per-chapter sizes (words are Pāḷi + English combined):

| Chapter | Words | Aligned pairs |
|---|---|---|
| Mv I | 83,268 | 2,705 |
| Mv II | 30,200 | 979 |
| Mv III | 17,540 | 620 |
| Mv IV | 23,705 | 671 |
| Mv V | 15,641 | 408 |
| Mv VI | 38,923 | 1,143 |
| Mv VII | 14,541 | 649 |
| Mv VIII | 30,781 | 1,005 |
| Mv IX | 29,840 | 879 |
| Mv X | 17,152 | 404 |
| **Total** | **301,591** | **9,463** |

Other classes present in the markup: `Commentary` (102 in chapter I), `Sub-commentary` (4),
`note` / `fn` (31 each), `sectionend` (82). A parser would need to decide whether commentary
spans become chunks, as the sutta parser already does with Ṭhānissaro's introductions.

## Licence

The Buddhist Monastic Code copyright page (`/vinaya/bmc/Section0002.html`) states verbatim:

> third edition, revised: 2025 Ṭhānissaro Bhikkhu. This work is licensed under the Creative
> Commons Attribution-NonCommercial 4.0 International. … "Commercial" shall mean any sale,
> whether for commercial or non-profit purposes or entities.

The Mahāvagga and Pāṭimokkha pages carry no per-page licence, and fall under the site-wide
CC BY-NC 4.0 statement already recorded in `docs/legal/legal-compliance-audit.md` §1.2. This is
the same licence as the repo's own `LICENSE`, so ingestion raises no new obligation beyond the
attribution gap §1.3 already tracks.

## Size against the current corpus

Current corpus: 1,405 dump files, 29,221 verses, ~1,044,764 English words.

| Candidate | English words | % of current corpus |
|---|---|---|
| Buddhist Monastic Code | 473,012 | +45% |
| Mahāvagga (English side) | ~150,000 | +14% |
| Both Pāṭimokkhas | 25,846 | +2% |
| **All three** | **~649,000** | **+62%** |

## What is not available

No translation on the site for the **Cullavagga** (the other twelve Khandhakas), the
**Suttavibhaṅga** (the canonical rule-by-rule analysis) or the **Parivāra**. Confirmed against
the ebook index, the Vinaya essays index and the Mahāvagga navigation. The Buddhist Monastic
Code paraphrases and quotes Suttavibhaṅga material, but is not a translation of it.
