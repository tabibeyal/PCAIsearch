import React, { Suspense } from 'react';
import { searchVerses } from '@/lib/api';
import { SynthesisLoader } from '@/components/deep-dive/SynthesisLoader';
import { SearchResultsView } from '@/components/search/SearchResultsView';

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

async function SearchContent({ query }: { query: string }) {
  try {
    const data = await searchVerses(query);
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
  const { view: viewParam } = await searchParams;
  const query = decodeURIComponent(rawQuery);
  const encodedQuery = encodeURIComponent(query);
  const view = viewParam === 'results' ? 'results' : 'synthesis';

  const tabClass = (active: boolean) =>
    `px-4 py-2 rounded-full text-sm font-medium transition-colors ${active ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`;

  return (
    <main className="h-screen w-full">
      <div className="flex flex-col h-full">
        <nav className="flex items-center p-4 bg-white border-b sticky top-0 z-10 gap-4">
          <a href="/" className="px-4 py-2 rounded-full text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors">
            ← New Search
          </a>
          <div className="flex-1 flex justify-center gap-4">
            <a href={`/search/${encodedQuery}?view=synthesis`} className={tabClass(view === 'synthesis')}>
              AI Synthesis
            </a>
            <a href={`/search/${encodedQuery}?view=results`} className={tabClass(view === 'results')}>
              All Verses
            </a>
          </div>
        </nav>
        <div className="flex-1 overflow-auto">
          {view === 'synthesis'
            ? <SynthesisLoader query={query} />
            : (
              <Suspense fallback={<LoadingState />}>
                <SearchContent query={query} />
              </Suspense>
            )}
        </div>
      </div>
    </main>
  );
}

export default SearchPage;
