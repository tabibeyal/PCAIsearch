# ADR-0003: Cloud Deployment Platform Selection

**Status:** Accepted  
**Date:** 2026-05-19

## Context

The application needs to move from local hardware to public web hosting. Constraints:
- Owner's local hardware is too weak to self-host
- Expected load: ~50,000 visitors/month (≈70/hour average, ≈400/hour peak)
- Budget ceiling: as low as possible
- Backend must load two ML models at startup: `paraphrase-multilingual-MiniLM-L12-v2` (~500MB) and `ms-marco-MiniLM-L-6-v2` (~200MB), requiring ≥1GB RAM
- The `/stream` endpoint uses Server-Sent Events (SSE); any platform that buffers HTTP responses breaks it
- NVIDIA LLM API (Llama 3.3 70B synthesis, Gemma 3n expansion) is free with 40 rpm limit — not a cost driver
- Qdrant collection: 134K vectors, 384 dims, ~320MB RAM footprint

## Decision

| Component | Platform | Cost |
|-----------|----------|------|
| Frontend (Next.js) | Vercel | Free |
| Vector DB | Qdrant Cloud free tier | Free |
| LLM inference | NVIDIA API | Free |
| Backend (FastAPI + ML models) | Fly.io | ~$7–10/month |

## Alternatives Considered

**Hugging Face Spaces (CPU free tier):** 16GB RAM, free for public spaces. Rejected because HF's HTTP proxy buffers responses, which breaks SSE streaming on the `/stream` endpoint.

**Render Standard ($25/month):** Sufficient RAM and reliable, but 2.5–3.5× more expensive than Fly.io for the same workload.

**Railway:** Billed by RAM/CPU minutes. A 1GB always-on container costs ~$20/month — more expensive than Fly.io.

**Single VPS (DigitalOcean/Hetzner):** Cheapest raw compute (~$6–12/month) but requires manual OS management, patching, and crash recovery. Rejected in favour of managed platforms to reduce ongoing maintenance.

## Consequences

- Backend is deployed as a Docker container on Fly.io with a 1GB RAM machine
- `QDRANT_URL` must be set as an environment variable (currently hardcoded to `localhost:6333`)
- `data/dumps/` must be committed to the repo (currently gitignored) so it is present in the Docker image
- Qdrant collection is migrated once via snapshot upload; not rebuilt on every deploy
- Free subdomains used initially (`*.vercel.app`, `*.fly.dev`); custom domain can be added later for ~$10–15/year
