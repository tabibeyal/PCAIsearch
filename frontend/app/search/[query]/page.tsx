import React from 'react';
import { getSynthesis, searchVerses } from '@/lib/api';
import { DualPaneContainer } from '@/components/deep-dive/DualPaneContainer';
import { SynthesisResponse, SearchResponse } from '@/types/api';
import { SearchResultsView } from '@/components/search/SearchResultsView';

async function SearchPage({ params, searchParams }: { params: Promise<{ query: string }>, searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
  const { query: rawQuery } = await params;
  const { view: viewParam } = await searchParams;
  const query = decodeURIComponent(rawQuery);
  const encodedQuery = encodeURIComponent(query);
  const view = viewParam === 'results' ? 'results' : 'synthesis';

  const tabClass = (active: boolean) =>
    `px-4 py-2 rounded-full text-sm font-medium transition-colors ${active ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`;

  const nav = (
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
  );

  try {
    let content: React.ReactNode;
    if (view === 'synthesis') {
      const synthesisData: SynthesisResponse = await getSynthesis(query);
      content = <DualPaneContainer data={synthesisData} />;
    } else {
      const searchData: SearchResponse = await searchVerses(query);
      content = <SearchResultsView results={searchData.results} query={query} />;
    }

    return (
      <main className="h-screen w-full">
        <div className="flex flex-col h-full">
          {nav}
          <div className="flex-1 overflow-auto">{content}</div>
        </div>
      </main>
    );
  } catch (error: any) {
    const isRateLimit = error.status === 429;
    return (
      <div className="h-screen flex items-center justify-center text-red-500 p-4 text-center">
        <div>
          <h1 className="text-2xl font-bold mb-2">{isRateLimit ? 'Rate Limit Exceeded' : 'Search Error'}</h1>
          <p>{isRateLimit ? 'You have sent too many requests. Please wait a moment and try again.' : 'Unable to retrieve search data for this query. Please check if the backend is running.'}</p>
          <a href="/" className="mt-4 inline-block text-blue-600 underline">Return to home</a>
        </div>
      </div>
    );
  }
}

export default SearchPage;
