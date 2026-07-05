"""Entry point for the daily Gap Detector run (see ADR-0004, CONTEXT.md § Gap detection).

Requires SUPABASE_URL / SUPABASE_KEY, QDRANT_URL / QDRANT_API_KEY, NVIDIA_API_KEY
in the environment, and an authenticated `gh` CLI in a clone of this repo.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.citation_oracle import CitationOracle
from backend.app.services.sutta_relations import SuttaRelations
from backend.app.services.sutta_title_index import SuttaTitleIndex
from backend.app.services.bm25_retriever import BM25Retriever
from backend.app.services.search_pipeline import SearchPipeline
from backend.app.services.supabase_client import SupabaseRestClient
from backend.app.services.feedback_store import SupabaseFeedbackStore
from backend.app.services.github_issue_tracker import GhIssueTracker
from backend.app.services.gap_detector import GapDetector

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

_DUMPS_DIR = Path(__file__).parent.parent / "data" / "dumps"


async def main() -> None:
    supabase_url = os.environ["SUPABASE_URL"].split("/rest/")[0].rstrip("/")
    supabase_key = os.environ["SUPABASE_KEY"]

    oracle = CitationOracle(_DUMPS_DIR)
    pipeline = SearchPipeline(
        sutta_relations=SuttaRelations(oracle.known_suttas),
        title_index=SuttaTitleIndex.from_directory(_DUMPS_DIR),
        bm25_retriever=BM25Retriever.from_directory(_DUMPS_DIR),
    )
    feedback_store = SupabaseFeedbackStore(SupabaseRestClient(supabase_url, supabase_key))
    issue_tracker = GhIssueTracker()

    try:
        filed = await GapDetector(feedback_store, pipeline, issue_tracker).run()
    finally:
        pipeline.shutdown()

    logger.info("Gap Detector filed %d issue(s): %s", len(filed), filed)


if __name__ == "__main__":
    asyncio.run(main())
