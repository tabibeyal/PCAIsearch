export interface PassageLine {
  id: string;
  english: string;
  isMatch: boolean;
}

export interface SearchResult {
  id: string;
  english: string;
  // Null on guarantee-filler entries (present only because the round-robin
  // book-representation policy forced their book in); the results view shows a
  // book-attribution badge instead of a match % for those (ADR-0008).
  score: number | null;
  passage?: PassageLine[];
  title?: string;
  title_pali?: string;
  title_english?: string;
  // Translator-commentary marker from the search API (#101). Absent on canon
  // verses; "commentary" on Thanissaro's introduction essays. The results view
  // renders a "Translator's introduction" label on flagged chunks (#104).
  section?: string;
  // True on results present only to guarantee their book a round-robin slot,
  // not because the reranker ranked them among the top-k on their own merits
  // (ADR-0008). Snake_case mirrors other backend-sourced fields on this type.
  is_guarantee_filler?: boolean;
}

export interface SynthesisResponse {
  query: string;
  answer: string;
  is_faithful: boolean;
  context: SearchResult[];
  receipt: string;
}

export interface SearchResponse {
  results: SearchResult[];
}
