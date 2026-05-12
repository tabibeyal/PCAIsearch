"use client";

import { useState, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type SearchResult = {
  sutta_id: string;
  title: string;
  text: string;
  score: number;
  source_url?: string;
};

type SynthesizeResponse = {
  query: string;
  answer: string;
  hallucinations: string[];
  is_faithful: boolean;
  context: SearchResult[];
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [answer, setAnswer] = useState<SynthesizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"search" | "synthesize">("synthesize");
  const inputRef = useRef<HTMLInputElement>(null);

  async function runSearch() {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResults([]);
    setAnswer(null);

    try {
      if (mode === "synthesize") {
        const res = await fetch(`${API_BASE}/synthesize?q=${encodeURIComponent(q)}`);
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const data: SynthesizeResponse = await res.json();
        setAnswer(data);
      } else {
        const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(q)}`);
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const data: { query: string; results: SearchResult[] } = await res.json();
        setResults(data.results);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") runSearch();
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 font-[family-name:var(--font-geist-sans)]">
      <main className="max-w-2xl mx-auto px-4 py-16 flex flex-col gap-8">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Ask the Pali Canon
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400 text-sm">
            Type a question or topic — find the suttas that answer it.
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex gap-2">
            <button
              onClick={() => setMode("synthesize")}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                mode === "synthesize"
                  ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700"
              }`}
            >
              Answer
            </button>
            <button
              onClick={() => setMode("search")}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                mode === "search"
                  ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700"
              }`}
            >
              Passages
            </button>
          </div>

          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                mode === "synthesize"
                  ? "What does the Buddha say about suffering?"
                  : "Search passages…"
              }
              className="flex-1 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-2.5 text-zinc-900 dark:text-zinc-50 placeholder-zinc-400 dark:placeholder-zinc-500 outline-none focus:ring-2 focus:ring-zinc-400 dark:focus:ring-zinc-500 text-sm"
            />
            <button
              onClick={runSearch}
              disabled={loading || !query.trim()}
              className="px-4 py-2.5 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 text-sm font-medium disabled:opacity-40 hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors"
            >
              {loading ? "…" : "Search"}
            </button>
          </div>
        </div>

        {error && (
          <p className="text-red-500 text-sm">{error}</p>
        )}

        {answer && (
          <div className="flex flex-col gap-6">
            <div className="rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-5">
              <p className="text-zinc-800 dark:text-zinc-200 text-sm leading-7 whitespace-pre-wrap">
                {answer.answer}
              </p>
              {!answer.is_faithful && (
                <p className="mt-3 text-xs text-amber-600 dark:text-amber-400">
                  ⚠ Some statements could not be verified against the source texts.
                </p>
              )}
            </div>

            {answer.context.length > 0 && (
              <div className="flex flex-col gap-3">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Source passages
                </h2>
                {answer.context.map((r, i) => (
                  <ResultCard key={i} result={r} />
                ))}
              </div>
            )}
          </div>
        )}

        {results.length > 0 && (
          <div className="flex flex-col gap-3">
            {results.map((r, i) => (
              <ResultCard key={i} result={r} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function ResultCard({ result }: { result: SearchResult }) {
  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
          {result.sutta_id}
        </span>
        <span className="text-xs text-zinc-400 dark:text-zinc-500">
          {(result.score * 100).toFixed(0)}% match
        </span>
      </div>
      {result.title && (
        <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
          {result.title}
        </p>
      )}
      <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-6 line-clamp-4">
        {result.text}
      </p>
      {result.source_url && (
        <a
          href={result.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 underline underline-offset-2 w-fit"
        >
          View on SuttaCentral
        </a>
      )}
    </div>
  );
}
