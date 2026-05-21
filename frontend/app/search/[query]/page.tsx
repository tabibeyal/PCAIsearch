import React, { Suspense } from 'react';
import { searchVerses } from '@/lib/api';
import { SynthesisLoader } from '@/components/deep-dive/SynthesisLoader';
import { SearchResultsView } from '@/components/search/SearchResultsView';
import { NikayaFilter } from '@/components/search/NikayaFilter';
import { NavSearchBox } from '@/components/search/NavSearchBox';

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full text-[#9c8c7a]">
      <div className="text-center">
        <div className="w-8 h-8 rounded-full animate-spin mx-auto mb-3" style={{ border: '2px solid #e8e4dc', borderTopColor: '#6b4e35' }} />
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
          <a href="/" className="mt-4 inline-block text-[#6b4e35] underline">Return to home</a>
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
    `px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${active ? 'bg-[#4a3728] text-white' : 'text-[#9c8c7a] hover:bg-[#ede8df]'}`;

  return (
    <main className="h-full w-full">
      <div className="flex flex-col h-full">
        <nav className="bg-[#faf9f7] border-b border-[#e8e4dc] sticky top-0 z-10">
          {/* Row 1: brand + search */}
          <div className="flex items-center gap-3 px-3 sm:px-4 pt-3 pb-2">
            <a href="/" className="text-sm text-[#9c8c7a] hover:text-[#6b4e35] whitespace-nowrap transition-colors">
              Home
            </a>
            <NavSearchBox initialQuery={query} />
          </div>
          {/* Row 2: tabs + filter */}
          <div className="flex items-center gap-2 px-3 sm:px-4 pb-3 flex-wrap">
            <a
              href={`/search/${encodedQuery}?view=synthesis${nikayas.map(n => `&nikayas=${n}`).join('')}`}
              className={tabClass(view === 'synthesis')}
            >
              AI Answer
            </a>
            <a
              href={`/search/${encodedQuery}?view=results${nikayas.map(n => `&nikayas=${n}`).join('')}`}
              className={tabClass(view === 'results')}
            >
              Passages
            </a>
            <div className="hidden sm:block w-px h-5 bg-[#e8e4dc]" />
            <NikayaFilter encodedQuery={encodedQuery} view={view} selected={nikayas} />
          </div>
        </nav>
        <div className="flex-1 min-h-0 overflow-auto">
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
