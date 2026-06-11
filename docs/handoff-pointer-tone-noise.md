# Handoff: Noisy Bullets in Pointer-Tone Responses

Branch: `feat/pointer-tone-system-prompt`

## Background

The system prompt was rewritten to shift the model from a "scholarly teacher" tone to a "pointer" tone — one orienting sentence, then bullets that each point to a distinct passage. This is working well for most queries. Three queries produce noisy or off-topic bullets; one query has a more serious problem.

---

## Issue 1: Off-topic bullets slipping through

**Queries affected:** consciousness, metaphysical speculation

The model sometimes cites a retrieved passage that doesn't directly address the query, then writes a bullet around it anyway. Examples:

- **Consciousness query** — one bullet cites a Māra/craving passage (STNP 5.12:4) and frames it as relevant to consciousness. The passage is about what Māra pursues people through, not about the nature of consciousness.
- **Metaphysical speculation query** — the final bullet cites MN 10:7 / DN 22:7 about how many years it would take to exhaust the topic of satipaṭṭhāna. Not about the limits of metaphysical speculation.

**Root cause:** The retriever is returning marginally relevant passages, and the small Llama model (3.1-8B) doesn't screen them out — it builds a bullet around whatever it was given.

**Possible fixes:**
- Prompt: add an instruction like "If a passage does not directly address the question, skip it — do not include it to pad the bullet count." (The grounding rule already says something similar but doesn't explicitly target this case.)
- Retrieval: tighten reranking thresholds so lower-scoring passages don't make it into the context window.

---

## Issue 2: Near-identical bullets from the same sutta

**Query affected:** not-self across suttas

Two bullets both cite MN 35 with almost identical content — one citing MN 35:16 and one citing MN 35:5. The consolidation instruction ("if several passages say essentially the same thing, consolidate them") didn't fire here because they are different verse numbers rather than different sutta IDs.

**Root cause:** The model treats each `[ID:verse]` as a distinct passage even when the content is nearly identical. The consolidation rule targets same-content passages but the model isn't recognising the overlap.

**Possible fix:** Strengthen the consolidation rule to apply at the content level, not just the ID level: "If two bullets would say essentially the same thing, merge them into one bullet regardless of whether their citation IDs differ."

---

## Issue 3: Model citing a bad retrieval match rather than skipping it

**Query affected:** concentration and insight

The DN 16:11 bullet describes the narrative framing of the Buddha as a teacher — "a comprehensive command of the Dhamma, a prodigious memory, and an untiring willingness to teach." This has nothing to do with concentration or insight. The model cited it anyway and tried to frame it as relevant.

This is a more serious version of Issue 1: not just a marginal passage, but a clearly wrong one.

The bullets for this query also quote passages at length in full quotation marks rather than paraphrasing and pointing. This feels like a regression toward the old teacher tone.

**Root cause:** Bad retrieval match made it into the top results; the small model can't reject it. The quote-heavy style may be the model defaulting to copying when it doesn't understand the passage well enough to paraphrase.

**Possible fixes:**
- Retrieval: this is primarily a reranking miss. The cross-encoder should score DN 16:11 very low against "concentration and insight" — worth checking whether it did and was overridden by fusion score.
- Prompt: "Never quote a passage at length. Paraphrase what it says in your own words, then cite it." (The existing grounding rule says to paraphrase but doesn't explicitly forbid direct quotation.)

---

## What is NOT a prompt problem

The server returned an empty response for the "spiritual capacity of women" query. That's a retrieval or timeout issue, not related to the tone change. Retry separately.

The gradual training bullets are long but substantive — each one is genuinely pointing to a different passage with real content. The length is a model tendency, not a format failure.
