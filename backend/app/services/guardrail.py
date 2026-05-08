import re
from typing import List, Dict, Any, Tuple

class CitationGuardrail:
    """
    Deterministic verification layer to prevent citation hallucinations.
    """
    def __init__(self):
        # Regex to find [ID:Verse] patterns, e.g., [DN 1:1], [MN 10:2]
        self.citation_pattern = re.compile(r"\[([A-Z\s]+ \d+:\d+)\]")

    def verify_citations(self, generated_text: str, retrieved_ids: List[str]) -> Tuple[str, List[str]]:
        """
        Scans text for citations and verifies them against the provided list of retrieved IDs.
        Returns the cleaned text and a list of hallucinated citations.
        """
        # Extract all citations found in the text
        found_citations = self.citation_pattern.findall(generated_text)

        retrieved_set = set(retrieved_ids)
        hallucinations = [c for c in found_citations if c not in retrieved_set]

        def _replace(m: re.Match) -> str:
            return "[Unverified]" if m.group(1) in hallucinations else m.group(0)

        verified_text = self.citation_pattern.sub(_replace, generated_text)
        return verified_text, hallucinations

    def process_response(self, response: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Full pipeline processing: Verify and flag response.
        """
        # Collect all canonical IDs from the retrieved context
        retrieved_ids = [chunk['id'] for chunk in context_chunks]

        cleaned_text, hallucinations = self.verify_citations(response, retrieved_ids)

        return {
            "text": cleaned_text,
            "hallucinations": hallucinations,
            "is_faithful": len(hallucinations) == 0
        }
