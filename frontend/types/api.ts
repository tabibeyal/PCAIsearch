export interface PassageLine {
  id: string;
  english: string;
  isMatch: boolean;
}

export interface SearchResult {
  id: string;
  pali: string;
  english: string;
  score: number;
  passage?: PassageLine[];
  title?: string;
  title_pali?: string;
  title_english?: string;
  // Translator-commentary marker from the search API (#101). Absent on canon
  // verses; "commentary" on Thanissaro's introduction essays. The results view
  // renders a "Translator's introduction" label on flagged chunks (#104).
  section?: string;
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
