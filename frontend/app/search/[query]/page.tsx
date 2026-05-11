import React, { Suspense } from 'react';
import { searchVerses } from '@/lib/api';
import { SynthesisLoader } from '@/components/deep-dive/SynthesisLoader';
import { SearchResultsView } from '@/components/search/SearchResultsView';
import { NikayaFilter } from '@/components/search/NikayaFilter';

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full text-gray-400">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm">Searching the Canon…</p>
      </div>
    </div>
  );
}

async function SearchContent({ query, nikayas }: { query: string; nikayas: string[] }) {
  try {
    const data = await searchVerses(query, 20, nikayas.length ? nikayas : undefined);
    return <SearchResultsView results={data.results} query={query} />;
  } catch (error: any) {
    const isRateLimit = error.status === 429;
    return (
      <div className="flex items-center justify-center p-8 text-red-500 text-center">
        <div>
          <h2 className="text-xl font-bold mb-2">{isRateLimit ? 'Rate Limit Exceeded' : 'Search Error'}</h2>
          <p>{isRateLimit ? 'You have sent too many requests. Please wait a moment and try again.' : 'Unable to retrieve search data for this query. Please check if the backend is running.'}</p>
          <a href="/" className="mt-4 inline-block text-blue-600 underline">Return to home</a>
        </div>
      </div>
    );
  }
}

async function SearchPage({
  params,
  searchParams,
}: {
  params: Promise<{ query: string }>;
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const { query: rawQuery } = await params;
  const { view: viewParam, nikayas: nikayasParam } = await searchParams;
  const query = decodeURIComponent(rawQuery);
  const encodedQuery = encodeURIComponent(query);
  const view = viewParam === 'results' ? 'results' : 'synthesis';
  const nikayas = Array.isArray(nikayasParam)
    ? nikayasParam
    : nikayasParam
    ? [nikayasParam]
    : [];

  const tabClass = (active: boolean) =>
    `px-4 py-2 rounded-full text-sm font-medium transition-colors ${active ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`;

  return (
    <main className="h-screen w-full">
      <div className="flex flex-col h-full">
        <nav className="flex items-center p-4 bg-white border-b sticky top-0 z-10 gap-4 flex-wrap">
          <a href="/" className="px-4 py-2 rounded-full text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors">
            ← New Search
          </a>
          <div className="flex gap-4">
            <a href={`/search/${encodedQuery}?view=synthesis${nikayas.map(n => `&nikayas=${n}`).join('')}`} className={tabClass(view === 'synthesis')}>
              AI Synthesis
            </a>
            <a href={`/search/${encodedQuery}?view=results${nikayas.map(n => `&nikayas=${n}`).join('')}`} className={tabClass(view === 'results')}>
              All Verses
            </a>
          </div>
          <div className="w-px h-6 bg-gray-200" />
          <NikayaFilter encodedQuery={encodedQuery} view={view} selected={nikayas} />
        </nav>
        <div className="flex-1 overflow-auto">
          {view === 'synthesis'
            ? <SynthesisLoader query={query} nikayas={nikayas} />
            : (
              <Suspense fallback={<LoadingState />}>
                <SearchContent query={query} nikayas={nikayas} />
              </Suspense>
            )}
        </div>
      </div>
    </main>
  );
}

export default SearchPage;
