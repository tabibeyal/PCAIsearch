import { SearchResult } from '@/types/api';

// The section value the search API sets on translator-commentary chunks (#101).
// Mirrors `backend/app/services/retriever.py` — absence of `section` means canon.
export const COMMENTARY_SECTION = 'commentary';

// A flagged result is translator commentary (Thanissaro's introduction essay),
// not canon text — the results view labels these "Translator's introduction" (#104).
export function isCommentaryResult(result: SearchResult): boolean {
  return result.section === COMMENTARY_SECTION;
}