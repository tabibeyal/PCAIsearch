export interface SearchResult {
  id: string;
  pali: string;
  english: string;
  score: number;
}

export interface SynthesisResponse {
  query: string;
  answer: string;
  hallucinations: string[];
  is_faithful: boolean;
  context: SearchResult[];
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}
