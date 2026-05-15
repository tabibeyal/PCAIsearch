# Philological cross-referencing is the goal; corpus expansion is downstream

**Status:** accepted, 2026-05-15

## Context

The PCAIsearch retrieval pipeline already does semantic search over the Sutta Piṭaka. The next direction was framed two ways in the same conversation: as "add Vinaya and Aṭṭhakathā in Pāḷi/English/Thai" (corpus expansion), and as "deeper philological cross-referencing — Pāḷi word clusters, parallel passages, commentary links" (feature work). These look like different projects but aren't — corpus expansion was being motivated *by* the cross-referencing goal: a graph of formulaic parallels is much richer once Vinaya and the commentaries are present.

## Decision

The goal is **philological cross-referencing**. Corpus expansion (Vinaya, Thai, Aṭṭhakathā) is a downstream prerequisite to be planned under that lens, not a parallel track and not the headline deliverable.

Concrete consequence: build the first cross-referencing feature (parallel-passage detection) on the existing Sutta-only corpus *before* ingesting Vinaya. The detector is corpus-agnostic; re-running it after each corpus expansion yields a strictly more complete graph. This decouples two large workstreams, lets the algorithm be iterated against a small fast corpus, and ensures Vinaya ingestion when it happens is shaped by what the philological tools have learned to care about (e.g. Brahmali's footnoted Sutta parallels become structural signal, not just rendered text).

## Considered and rejected

- *Corpus-expansion-first.* The natural reading of "I want to add the Vinaya and Aṭṭhakathā" — ingest first, build features after. Rejected because it blocks the actual goal behind weeks of ingestion work, forces ingestion design decisions to be made without knowing what the philological layer needs, and produces a bigger corpus that's still searched the same shallow way.
- *Both in parallel.* Rejected: ingestion design decisions (chunk-ID scheme, schema fields, edge metadata) depend on what the cross-referencing layer turns out to need. Doing them in parallel risks redoing ingestion.

## Consequences

- The first user-visible deliverable will surface parallels over the Sutta Piṭaka only. Cross-pitaka parallels (Sutta↔Vinaya) — arguably the most interesting category — are deferred to Phase 2.
- Vinaya ingestion, when scheduled, gets re-planned from scratch rather than continuing the abandoned Vinaya-first sketch.
- `CONTEXT.md` records the phase ordering: Phase 1 parallel passages (Sutta), Phase 2 Vinaya ingestion + re-run detector, Phase 3 Aṭṭhakathā + commentary edges.
