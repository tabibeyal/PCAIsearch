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
