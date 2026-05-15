# Span-based parallel-passage detection: design choices

**Status:** accepted, 2026-05-15

## Context

We are building an offline batch tool that detects recurring Pāḷi formulas across the Sutta corpus and emits a queryable graph. Three design choices were made that go *against* the default each defaults would be the opposite. Once the artifact is built and downstream tooling (CLI queries, future API, future UI) is built on top, reversing any of these would require regenerating the artifact and changing every consumer. They are recorded here so a future reader does not "fix" them.

## Decisions

### 1. The node is a **span**, not a verse-pair or sutta-pair

A span is a *maximal recurring sequence of normalised Pāḷi tokens*, identified by content hash. Each span has a list of occurrences; an occurrence is `(sutta_id, verse_number, char_offset, char_length)`.

The obvious alternatives — verse-pair edges ("MN 27:14 parallels DN 2:42") or sutta-pair edges ("MN 27 and DN 2 share content") — were rejected because they don't match the linguistic reality. Pāḷi stock formulas are arbitrary-length text units that almost never align with editorial verse boundaries; declaring "verse A ≈ verse B" is wrong whenever the parallel is only a substring of each. Span-based representation gives the exact recurring text as the first-class thing, and both other views (verse-pair, sutta-pair) are trivial `GROUP BY`s over it. The reverse — reconstructing the shared text from a verse-pair edge — is impossible without re-running detection.

### 2. Tokenisation is **per-sutta**, not per-verse

Bilara segmentation is fine-grained (often one segment per sentence). The jhāna formula occupies 4–6 segments; *paticcasamuppāda* more; the satipaṭṭhāna refrain spans several. Per-verse tokenisation would silently fragment every long formula into 4–6 shorter independent spans, losing structural unity. Per-sutta tokenisation lets spans cross verse boundaries; the occurrence record stores the *starting* `(verse_number, char_offset)`, and reconstruction walks subsequent verses if needed. This adds ~30 LOC of reconstruction logic; the gain is that the artifact contains the formulas that actually exist rather than editorial fragments of them.

### 3. Normalisation is **light only**, no lemmatisation, no sandhi splitting, no stop-word removal

The normalisation pipeline is: NFC, lower-case, strip punctuation, collapse whitespace, canonicalise niggahita (ṁ/ṃ → one form). Nothing else.

This catches the exact-formula repetition that dominates the canon (oral-tradition mnemonic structure preserves stock formulas byte-stably modulo surface cleanup). Heavier normalisation — lemmatisation via DPD or pyrkz, stop-particle stripping, sandhi splitting — was rejected because it imports the morphological analyser's error rate into our output, conflates real distinctions (singular/plural, tense/aspect that carry doctrinal meaning), and turns parallel-passage detection into approximate semantic similarity (which embeddings already handle differently and better). The cases light normalisation misses (inflectional variants of the same formula) are the explicit target of a *later, separate* "Pass 2" fuzzy-matching layer — a new edge type on the same schema, not a re-normalisation of the existing one.

## Consequences

- Changing any of these three later means rebuilding the artifact. With Sutta-only that is seconds; with Sutta+Vinaya+Aṭṭhakathā it will be minutes-to-an-hour plus any downstream cache/UI invalidation. Treat them as locked.
- A future "near-parallel" / fuzzy-match feature is intended as an *additional* edge type on the existing `span`/`occurrence` tables, not as a replacement for the current exact-match detector.
- Span IDs being content-addressed (hash of normalised text) means a given formula gets the same ID across corpus rebuilds — Vinaya ingestion in Phase 2 *adds occurrences to existing spans* rather than re-keying them. This was a deliberate property and should be preserved.
- The artifact records `detector_version` per span row; changing the algorithm or normalisation must bump this string. Mixing versions in one file is supported but should be exceptional.
