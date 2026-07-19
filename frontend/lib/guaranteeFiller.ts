import { SearchResult } from '@/types/api';

// A flagged result is a guarantee filler: present only because the round-robin
// book-representation policy forced its book into the result set, not because
// the reranker ranked it among the top-k on its own merits. The results view
// shows a book-attribution badge instead of a match % (ADR-0008).
export function isGuaranteeFillerResult(result: SearchResult): boolean {
  return result.is_guarantee_filler === true;
}