#!/usr/bin/env bash
# Run the recall@10 benchmark with LLM query expansion.
#
# Requires NVIDIA_API_KEY, QDRANT_URL, and QDRANT_API_KEY in the environment
# (these are in .env at the repo root, which the script sources if present).
#
# Usage:
#   ./scripts/run_recall_benchmark.sh
#   ./scripts/run_recall_benchmark.sh --k 20          # override k
#   ./scripts/run_recall_benchmark.sh --no-rerank     # reranker off
#
# Output to watch: the final line, "Overall recall@10: X/15 (NN%)".

set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${NVIDIA_API_KEY:?NVIDIA_API_KEY must be set (check .env)}"
: "${QDRANT_URL:?QDRANT_URL must be set (check .env)}"

PYTHONPATH=. python3 tests/backend/retrieval_benchmark.py --with-expansion --log-variants "$@"
