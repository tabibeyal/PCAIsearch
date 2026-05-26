#!/bin/bash
# Local dev server — connects to Qdrant Cloud so the collection is available
# Loads credentials from .env (never commit that file)
set -a
# shellcheck source=.env
source "$(dirname "$0")/.env"
set +a

PYTHONPATH=. uvicorn backend.app.main:app --reload "$@"
