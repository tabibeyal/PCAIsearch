import re
from typing import Any, Dict, List, Optional, Tuple

from backend.app.services.citation_oracle import CitationOracle


class CitationGuardrail:
    """
    Deterministic verification layer to prevent citation hallucinations.

    With a CitationOracle, distinguishes two failure modes:
    - hallucinations: citations to sutta IDs that don't exist in the canon
    - canonical_misses: citations to real suttas that weren't in the retrieved context

    Without a CitationOracle, any citation not in retrieved chunks
    is treated as a hallucination.
    """

    def __init__(self, oracle: Optional[CitationOracle] = None):
        self.citation_pattern = re.compile(r"\[([A-Z\s]+ \d+:\d+)\]")
        self.oracle = oracle

    def verify_citations(
        self, generated_text: str, retrieved_ids: List[str]
    ) -> Tuple[str, List[str], List[str]]:
        """
        Scan text for [ID:Verse] citations and classify each.

        Returns:
            (verified_text, hallucinations, canonical_misses)
            - hallucinations: citations not in the canon at all
            - canonical_misses: citations in the canon but not in retrieved context
        """
        found = self.citation_pattern.findall(generated_text)
        retrieved_set = set(retrieved_ids)
        hallucinations: List[str] = []
        canonical_misses: List[str] = []

        for citation in found:
            if citation in retrieved_set:
                continue
            if self.oracle and self.oracle.citation_in_canon(citation):
                canonical_misses.append(citation)
            else:
                hallucinations.append(citation)

        hallucination_set = set(hallucinations)
        canonical_miss_set = set(canonical_misses)

        def _replace(m: re.Match) -> str:
            c = m.group(1)
            if c in hallucination_set:
                return "[Hallucinated]"
            if c in canonical_miss_set:
                return "[Unverified]"
            return m.group(0)

        verified_text = self.citation_pattern.sub(_replace, generated_text)
        return verified_text, hallucinations, canonical_misses

    def process_response(
        self, response: str, context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Verify citations and return structured result."""
        retrieved_ids = [chunk["id"] for chunk in context_chunks]
        cleaned_text, hallucinations, canonical_misses = self.verify_citations(
            response, retrieved_ids
        )
        return {
            "text": cleaned_text,
            "hallucinations": hallucinations,
            "canonical_misses": canonical_misses,
            "is_faithful": len(hallucinations) == 0,
        }
