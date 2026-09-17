# Does the Vinaya fit the budget we already pay?

Research for [#188](https://github.com/tabibeyal/PCAIsearch/issues/188), ticket of the map
[Bring the Vinaya into the corpus](https://github.com/tabibeyal/PCAIsearch/issues/179).
Builds on the source survey in [`vinaya-sources.md`](vinaya-sources.md) ([#180](https://github.com/tabibeyal/PCAIsearch/issues/180)).
Measured 2026-09-17. This report decides nothing — the go/no-go belongs to whoever sequences
the work.

## Summary of findings

1. **The vector database has enormous room.** The live collection uses about **48 MB of the
   1 GB** the free tier allows — roughly 5%. Adding the Vinaya takes that to about 9%. Even the
   version that also stores the Pāḷi text lands near 10%. **No tier change is needed.**
2. **The "320 MB" figure everyone has been quoting describes a corpus that no longer exists.**
   It comes from `ADR-0003` and describes the *old* Sujato corpus of 134,102 vectors. Today's
   collection holds **29,221** — 4.6 times fewer. The real footprint is 48 MB, not 320 MB.
3. **Issue [#115](https://github.com/tabibeyal/PCAIsearch/issues/115) is partly stale.** The
   nikāya filter that it says is impossible **now works** on production. A keyword index over
   the `nikaya` field exists and covers all 29,221 points; a filtered search returns results in
   under 3 ms. Only the `section` field (used to hide translator commentary) is still
   unindexed, and only that one filter still has to be done in Python.
4. **Growing the corpus does not make the Python post-filter more expensive.** Measured against
   production, asking Qdrant for 200 candidates instead of 10 costs the same 1–2 ms. And the
   share of the corpus being filtered out *falls* from 6.2% to about 3.8% when the Vinaya
   arrives, because the Vinaya adds no commentary-marked chunks.
5. **The backend server is where the pressure actually is.** The text-search machinery that
   lives in the server's memory grows in a straight line with the corpus: measured at
   **0.099 MB per thousand English words**. The Vinaya's 649,000 words therefore add about
   **64 MB** for the keyword index alone and roughly **106 MB** across all four in-memory
   structures.
6. **That fits the server we actually run.** The backend is a **DigitalOcean App Platform
   component with 2 GB RAM and 1 shared vCPU, billed at $25.00/month** (read off the dashboard
   by the project owner on 2026-09-17). The best estimate of memory use today is ~1.3 GB of
   that 2 GB. Adding the Vinaya makes it ~1.4 GB — about 70% full.
7. **The real bill is already double what the docs claim.** `README.md` and `CONTEXT.md` say
   "~$7–12/month"; the confirmed figure is $25/month for the backend alone. That gap exists
   today and has nothing to do with the Vinaya, but any budget conversation should start from
   $25, not $12.

---

## Terms used in this report

- **Vector** — a list of 384 numbers that stands for the meaning of one passage. The search
  works by comparing vectors, not words.
- **Point** — one stored record in the vector database: a vector plus its text and labels.
  One point equals one chunk of a sutta. This corpus has 29,221 of them.
- **Payload** — the plain text and labels stored next to each vector (the English, the
  sutta ID, the nikāya).
- **Payload index** — a lookup table that lets the database filter by a label (e.g. "only MN")
  quickly. Without one, Qdrant's free tier refuses the filter outright.
- **BM25** — old-fashioned keyword matching, used alongside the vector search to catch exact
  wording. Its index is built fresh in the server's memory every time the app starts.
- **RSS** — "resident set size", the amount of memory a running program actually occupies.
- **HNSW** — the graph structure the vector database walks to find near neighbours fast. It
  costs extra memory on top of the vectors themselves.

---

## 1. Qdrant Cloud — the vector database

### What is actually there today (measured)

Queried live against the production cluster on 2026-09-17 via the Qdrant REST API
(`GET /collections/pali_canon` and `GET /telemetry?details_level=3`, credentials from
`/home/eyal/PCAIsearch/.env`). Read-only calls only.

| Fact | Value | Source |
|---|---|---|
| Points in the collection | **29,221** | `points_count` |
| Vectors already indexed | 26,684 | `indexed_vectors_count` |
| Vector size / distance | 384 dims, Cosine | `config.params.vectors` |
| Bytes of vectors | **44,883,456** (42.8 MiB) | telemetry `vectors_size_bytes` |
| Bytes of payload | **8,197,504** (7.8 MiB) | telemetry `payloads_size_bytes` |
| Payload stored on disk, not RAM | `on_disk_payload: true` | `config.params` |
| HNSW graph kept in RAM | `hnsw_config.on_disk: false` | `config` |
| Shards | 1 | `cluster` |
| Qdrant version | 1.18.0 | telemetry `app.version` |

The vector figure checks out exactly: 29,221 × 384 dimensions × 4 bytes = 44,883,456 bytes.
Nothing is being estimated there.

The same telemetry reports the *host machine* as having 16,146,520 KB of RAM. That is the
shared server the free cluster sits on, **not** the quota. The quota is what the pricing page
states, below.

### What the free tier allows (primary source)

Qdrant's pricing page states the Free Tier is a "Single Node Cluster" with
**"0.5 vCPU / 1GB RAM / 4 GB Disk"**, "Free forever", intended "For testing, and prototypes"
(<https://qdrant.tech/pricing/>). Qdrant's own documentation adds that this configuration fits
roughly one million 768-dimension vectors — which is two million at this project's 384
dimensions.

Free clusters are suspended after 1 week of inactivity and deleted after 4 weeks
(<https://qdrant.tech/documentation/cloud/create-cluster/>). This project's cluster has been up
since 2026-05-26 (telemetry `startup`), so that has never bitten.

### How much RAM the collection needs

Qdrant publishes the arithmetic at
<https://qdrant.tech/documentation/capacity-planning/>. Applying it to the measured numbers:

| Component | Qdrant's formula | Today (29,221 points) |
|---|---|---|
| Vectors | `points × dims × 4 bytes` | 44.9 MB (42.8 MiB) |
| HNSW graph | `points × m × 2 × 4 bytes × 1.2` (m = 16) | 4.5 MB (4.3 MiB) |
| ID tracker (always in RAM) | `points × 52 bytes` | 1.5 MB (1.45 MiB) |
| Payload | on disk — see `on_disk_payload: true` | 0 |
| **Subtotal** | | **50.9 MB (48.5 MiB)** |
| Qdrant's "~20% headroom" rule | | **61 MB (58 MiB)** |

**That is 5.7% of the 1 GB ceiling.**

### Where the Vinaya lands (estimate, arithmetic shown)

The corpus averages 1,044,764 English words across 29,221 chunks — **35.8 words per chunk**
(measured by parsing `data/dumps/` locally). Assuming the Vinaya is chunked at a similar
paragraph size, which is the same shape of prose from the same translator:

| Scenario | Added words | Added points | Total points | RAM (+20%) | % of 1 GB |
|---|---|---|---|---|---|
| Today | — | — | 29,221 | 61 MB | **5.7%** |
| Monastic Code only (#181's choice, +45%) | 473,012 | ~13,200 | ~42,400 | 88 MB | **8.2%** |
| All three English sources (+62%) | 649,000 | ~18,100 | ~47,300 | 99 MB | **9.2%** |
| …plus Mahāvagga Pāḷi (+76%) | ~799,000 | ~22,300 | ~51,500 | 108 MB | **10.0%** |

*Estimate.* The added-point counts assume the Vinaya chunks at the corpus's current average of
35.8 words. If the *Monastic Code*'s paragraphs run twice as long, the point count halves and
the RAM figures fall; if they run half as long, both double — and even at double, the
Pāḷi-inclusive case reaches 20% of the ceiling. **There is no chunk size within reach that
breaks the free tier.**

Disk is even less of a concern: 44.9 MB of vectors + 8.2 MB of payload = 53 MB today, about
**1.6% of the 4 GB disk**. The Pāḷi-inclusive case lands near 112 MB, or 2.8%.

### The filtering question (#115) — the premise has changed

Issue #115 records that any filtered query against the collection returns
`400 Bad Request: "Index required but not found for \"nikaya\""`, and that the free tier
refuses to create the index.

**That is no longer what production does.** Measured 2026-09-17:

- `GET /collections/pali_canon` reports
  `"payload_schema": {"nikaya": {"data_type": "keyword", "points": 29221}}` — **the index
  exists and covers every point.**
- A filtered vector search (`POST /points/query` with
  `filter: {must: [{key: "nikaya", match: {any: ["MN"]}}]}`) **returns results**, in 2.7 ms.
- A filtered count returns MN = 5,975 in 0.8 ms.

What *is* still true is the other half. The collection runs with
`strict_mode_config.unindexed_filtering_retrieve: false`, so filtering on a field with no index
is refused. Filtering on `section` — the field that marks translator commentary — still fails:

> `Bad request: Index required but not found for "section" of one of the following types: [keyword].`

So `backend/app/services/retriever.py:47-54` is still correct about commentary: it over-fetches
and drops commentary chunks in Python. But the comment at `backend/app/main.py:112-113`
("Qdrant Cloud free tier returns 403 for index management operations") is contradicted by the
index that now exists. **Worth a separate ticket — it changes what #115 is about.**

Note also `strict_mode_config.max_payload_index_count: 100`. The collection currently uses one
of those hundred. A Vinaya `section` index, if creation is in fact permitted, is well within it.

### Does a bigger corpus make post-filtering more expensive?

The issue's worry is that filtering in Python means fetching more candidates, and a bigger
corpus means fetching more still. **Measured, it does not.**

`retriever.py:11-12` over-fetches `top_k × 4`, capped at 200, when commentary must be excluded.
Timings from production (server-side `time` field, three runs each):

| Request | Server time |
|---|---|
| limit 10, no filter | 0.97 / 1.00 / 1.08 ms |
| limit 40, no filter | 1.48 / 1.13 / 1.06 ms |
| limit 200, no filter | 1.52 / 1.37 / 2.08 ms |
| limit 10, filtered to DN (the smallest full nikāya, 2,992 points) | 2.99 ms |
| limit 200, filtered to DN | 1.86 ms |

Asking for twenty times as many candidates costs essentially nothing. The reason is structural:
the HNSW graph is walked to find the best *N* results, and that walk does not get twenty times
longer because *N* went from 10 to 200, nor proportionally longer because the corpus grew.

And the pressure on the post-filter **decreases**. Commentary is 1,821 of 29,221 chunks today —
**6.2%** (measured by parsing `data/dumps/`). Under #181's choice, the *Monastic Code* is
English prose with no translator-commentary marking, so it adds none. At 47,300 points, the
same 1,821 commentary chunks are **3.8%** of the corpus. A 4× over-fetch that clears a 6.2%
filter clears a 3.8% one with more room, not less.

Per-nikāya point counts, for reference (exact counts, measured):
DN 2,992 · MN 5,975 · SN 7,665 · AN 6,436 · STNP 919 · DHP 462.

---

## 2. Backend RAM — the server that runs the search

### What loads into memory at startup

`backend/app/main.py:98-116` builds **four** separate in-memory structures from the same
`data/dumps/` folder, plus two machine-learning models:

| Structure | Built at | What it holds |
|---|---|---|
| `CitationOracle` | `main.py:98` | which verse numbers exist, for checking the AI's citations |
| `SuttaTitleIndex` | `main.py:99` | a **second BM25 keyword index**, over titles and opening verses |
| `BM25Retriever` | `main.py:100` | the **main BM25 keyword index**, over every verse |
| `PassageStore` | `main.py:116` | every verse's text, so a citation can be shown in context |

The BM25 index is **held fully in memory**, as the issue suspected.
`backend/app/services/bm25_retriever.py:16-19` keeps the full list of verse dictionaries
(`self._verses`) *and* builds a `BM25Okapi` over a tokenised copy of every verse. Nothing is
memory-mapped or paged to disk. `sutta_title_index.py:18-25` does the same thing a second time
on a smaller set.

### Measured footprint (local, no models loaded)

Measured on 2026-09-17 by importing the real classes against the real `data/dumps/` and reading
peak RSS from `resource.getrusage`, each in its own process so the numbers do not contaminate
each other. No embedding model was loaded.

| Structure | Peak memory added |
|---|---|
| `CitationOracle` | 3.5 MiB |
| `SuttaTitleIndex` | 57.7 MiB |
| `PassageStore` | 17.0 MiB |
| `BM25Retriever` | 126.3 MiB |
| **All four together** | **171.2 MiB** |

(The individual figures include short-lived memory used while parsing the JSON, so they add up
to more than the combined figure. The combined figure is the one that matters.)

### How the BM25 index scales (measured, linear)

Built over three different fractions of the corpus and measured the memory the build added:

| Corpus fraction | Verses | English words | Memory added | Per 1,000 words |
|---|---|---|---|---|
| 25% of files | 5,269 | 187,976 | 18.6 MiB | 0.099 MiB |
| 50% of files | 18,735 | 718,385 | 70.1 MiB | 0.098 MiB |
| 100% | 29,221 | 1,044,764 | 103.2 MiB | 0.099 MiB |

**0.099 MB per thousand English words**, dead straight across a fivefold range. That is a
measured coefficient, not a guess.

Applying it:

| Scenario | Added words | Added BM25 memory | All four structures (est.) |
|---|---|---|---|
| Monastic Code only (+45%) | 473,012 | **+47 MB** | ~+77 MB → ~248 MB |
| All three English (+62%) | 649,000 | **+64 MB** | ~+106 MB → ~277 MB |
| …plus Mahāvagga Pāḷi (+76%) | ~799,000 | **+79 MB** | ~+130 MB → ~301 MB |

*Estimate note.* The "all four" column scales the measured 171.2 MiB total by the same
percentage. That is slightly pessimistic for `SuttaTitleIndex`, which grows with the *number of
suttas* rather than total words — and the Vinaya is a small number of large documents. It is
slightly optimistic for `PassageStore` if the Mahāvagga's Pāḷi is stored, since Pāḷi is stored
as extra text per verse.

### What else is in that server's memory

This is the part that decides whether +106 MB matters. Measured locally by importing the
libraries only — **no model weights loaded**:

| Loaded | Peak RSS |
|---|---|
| Bare Python | 8 MiB |
| + `torch` | 481 MiB |
| + `onnxruntime` | 494 MiB |
| + `sentence_transformers` | 814 MiB |
| + `fastembed` | **816 MiB** |

**The libraries alone cost 816 MB before a single model weight is read.** On top of that sit
the model files themselves, measured on disk from the local cache: the embedding model
(`paraphrase-multilingual-MiniLM-L12-v2`, ONNX, quantised) is **241 MB**, and the reranker
(`ms-marco-MiniLM-L-6-v2`) is **88 MB**. Both are downloaded at image-build time
(`Dockerfile:36-38`).

**Estimated total today: ~816 MB libraries + ~330 MB model weights + ~171 MB corpus
structures ≈ 1.3 GB.** Labelled an estimate because the three parts were measured separately
and some memory (shared library pages) is counted twice; the true figure is likely a little
lower. Adding the Vinaya at +62% takes it to roughly **1.4 GB**.

For corroboration: `digitalocean-model-settings.txt` warns that running the backend with
`--reload` locally "loads the 1.6 GB of models twice and freezes the laptop" — the same order
of magnitude, arrived at independently by someone who watched it happen.

### How big is the server? — confirmed from the dashboard

**Confirmed 2026-09-17 by the project owner, reading the DigitalOcean dashboard:** the backend
is an **App Platform** component sized **2 GB RAM / 1 shared vCPU / 200 GB bandwidth, 1
container, $25.00/month**. The section below records why this had to be asked, and what it
corrects.

**The repo contains no DigitalOcean app spec.** There is no `.do/app.yaml`, no
`instance_size_slug` anywhere, and nothing in `.github/` that names one. The written evidence
was contradictory:

- `docs/adr/0003-cloud-deployment-platform.md:24,38` says **"DigitalOcean (2GB Droplet)"**
  at "~$7–12/month".
- `README.md:47` and `CONTEXT.md:31` say **"DigitalOcean App Platform"** at "~$7–12/month".

The dashboard settles it: **App Platform is right, and the "~$7–12/month" figure in both
files is wrong.** From DigitalOcean's own pricing pages:

| Option | RAM | Price/mo | Source |
|---|---|---|---|
| Droplet, Basic shared | 1 GiB / 1 vCPU | $6.00 | <https://www.digitalocean.com/pricing/droplets> |
| **Droplet, Basic shared** | **2 GiB / 1 vCPU** | **$12.00** | same |
| Droplet, Basic shared | 4 GiB / 2 vCPU | $24.00 | same |
| App Platform, shared fixed | 1 GiB / 1 vCPU | $10.00 | <https://www.digitalocean.com/pricing/app-platform> |
| App Platform, shared | 1 GiB / 1 vCPU | $12.00 | same |
| App Platform, shared | 2 GiB / 1 vCPU | $25.00 | same |

The confirmed line is the last one: **App Platform, 2 GiB shared, $25.00/month.** Two
consequences:

1. **ADR-0003's "2GB Droplet" is stale as to platform, right as to memory.** The move to App
   Platform is recorded in `README.md:47` and `CONTEXT.md:31`; the ADR was never updated. The
   2 GB working figure used throughout this report is correct.
2. **The "~$7–12/month" budget in `README.md` and `CONTEXT.md` is wrong and should be
   corrected** — the backend alone is $25/month. This is a documentation defect that predates
   the Vinaya question and deserves its own ticket.

The App Platform 1 GiB options, at $10–12, **cannot hold 816 MB of libraries plus 330 MB of
weights**, so downgrading to reach the old $12 figure is not available.

**On the assumption of 2 GB:** ~1.3 GB today, ~1.4 GB with the Vinaya, out of 2 GB. That fits,
with roughly 600 MB spare. It is not comfortable — it is the difference between 65% and 70%
full — but the Vinaya is not what would push it over.

Also worth noting: `ADR-0003` records that a Netlify/DigitalOcean pairing was chosen partly
because Hugging Face's free 16 GB tier breaks the `/stream` endpoint. Memory pressure is not
the only constraint on where this runs.

---

## 3. The cheapest paid step, if one is ever needed

| If the pinch is… | The step is | Cost |
|---|---|---|
| **Qdrant RAM** | Not needed. 5.7% used today, ~9–10% with the Vinaya. Qdrant publishes no fixed price for the paid Standard tier — it is usage-billed and directed to a calculator (<https://qdrant.tech/documentation/cloud-pricing-payments/>). Third-party trackers put the smallest paid cluster in the $25–115/month range; **none of these is a primary source and none should be relied on.** | **$0** |
| **Qdrant disk** | Not needed. 1.6% of 4 GB used. | **$0** |
| **Backend RAM** | Not needed. Already on App Platform 2 GiB shared at **$25/mo** (confirmed 2026-09-17); ~1.3 GB used today, ~1.4 GB with the Vinaya, i.e. ~70% of 2 GB. | **$0 extra** |

**Nothing here requires a paid step.** Every part of the Vinaya expansion fits inside what the
project pays right now. The separate, pre-existing problem is that what the project pays right
now is $25/month, not the ~$7–12/month its own docs claim.

One genuinely free lever exists if memory ever does become tight. `SuttaTitleIndex` costs
57.7 MB to hold a second BM25 index whose corpus is titles plus verses 3–15 of each sutta
(`sutta_title_index.py:65-69`). Whether the Vinaya needs to be in *that* index at all is a
design choice, not a cost.

---

## What this report does not answer

- **The price of the next App Platform size up.** Not needed by any measurement here, so it
  was never looked up. If a bigger container is ever wanted, price it against
  <https://www.digitalocean.com/pricing/app-platform> at that time.
- **How the Vinaya actually chunks.** Every point-count figure here assumes 35.8 words per
  chunk, the current corpus average. The *Monastic Code* is explanatory prose with long
  paragraphs and may chunk very differently. This becomes measurable the moment a parser exists,
  and it is the single input that moves all the Qdrant numbers.
- **Whether the nikāya index survives a reindex.** The index exists today, but nobody recorded
  creating it, and the code at `main.py:106-114` expects creation to fail. If the collection is
  ever rebuilt, the index may or may not come back — which would reopen #115 in earnest.
- **Latency under real load.** All timings here are single requests against an idle cluster with
  a random query vector. They establish that over-fetching is cheap; they do not establish
  end-to-end search latency.
- **Whether recall survives the addition.** Out of scope here, but #117 (the open recall
  regression) is already flagged on #179 as a reason to be careful about when this lands.

---

## Sources

**Live measurement, 2026-09-17** — Qdrant REST API against the production cluster
(`GET /collections`, `GET /collections/pali_canon`, `GET /telemetry?details_level=3`,
`POST /collections/pali_canon/points/query`, `POST .../points/count`,
`POST .../points/scroll`). Credentials from `/home/eyal/PCAIsearch/.env`. Read-only throughout;
nothing was written or deleted.

**Local measurement, 2026-09-17** — Python scripts against `/home/eyal/PCAIsearch/data/dumps/`
(1,405 files, 8,743,773 bytes on disk), reading peak RSS from `resource.getrusage`. No
embedding or reranking model was loaded at any point.

**Repo files** — `backend/app/main.py`, `backend/app/services/bm25_retriever.py`,
`backend/app/services/retriever.py`, `backend/app/services/sutta_title_index.py`,
`backend/app/services/passage_context.py`, `backend/app/services/citation_oracle.py`,
`Dockerfile`, `docs/adr/0003-cloud-deployment-platform.md`, `CONTEXT.md`, `README.md`,
`digitalocean-model-settings.txt`.

**Vendor documentation** — <https://qdrant.tech/pricing/> ·
<https://qdrant.tech/documentation/capacity-planning/> ·
<https://qdrant.tech/documentation/cloud-pricing-payments/> ·
<https://qdrant.tech/documentation/cloud/create-cluster/> ·
<https://www.digitalocean.com/pricing/droplets> ·
<https://www.digitalocean.com/pricing/app-platform>

**Corpus sizes** — [`docs/research/vinaya-sources.md`](vinaya-sources.md) (#180).
