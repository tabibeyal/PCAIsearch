import React from 'react';
import Link from 'next/link';
import { SynthesisLoader } from '@/components/deep-dive/SynthesisLoader';
import { SearchResultsLoader } from '@/components/search/SearchResultsLoader';
import { NikayaFilter } from '@/components/search/NikayaFilter';
import { NavSearchBox } from '@/components/search/NavSearchBox';
import { SupportBanner } from '@/components/SupportBanner';
import { SupportBannerProviderBoundary } from '@/components/SupportBannerProviderBoundary';

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
      <SupportBannerProviderBoundary>
        <div className="flex flex-col h-full">
          <nav className="bg-[#faf9f7] border-b border-[#e8e4dc] sticky top-0 z-10">
            {/* Row 1: brand + search */}
            <div className="flex items-center gap-3 px-3 sm:px-4 pt-3 pb-2">
              <Link href="/" className="text-sm text-[#9c8c7a] hover:text-[#6b4e35] whitespace-nowrap transition-colors">
                Home
              </Link>
              <NavSearchBox initialQuery={query} />
            </div>
            {/* Row 2: tabs + filter */}
            <div className="flex items-center gap-2 px-3 sm:px-4 pb-3 flex-wrap">
              <Link
                href={`/search/${encodedQuery}?view=synthesis${nikayas.map(n => `&nikayas=${n}`).join('')}`}
                className={tabClass(view === 'synthesis')}
                scroll={false}
              >
                AI Answer
              </Link>
              <Link
                href={`/search/${encodedQuery}?view=results${nikayas.map(n => `&nikayas=${n}`).join('')}`}
                className={tabClass(view === 'results')}
                scroll={false}
              >
                Passages
              </Link>
              <div className="hidden sm:block w-px h-5 bg-[#e8e4dc]" />
              <NikayaFilter encodedQuery={encodedQuery} view={view} selected={nikayas} />
            </div>
          </nav>
          <div className="flex-1 min-h-0 overflow-auto">
            {view === 'synthesis'
              ? <SynthesisLoader query={query} nikayas={nikayas} />
              : <SearchResultsLoader query={query} nikayas={nikayas} />}
          </div>
          <SupportBanner />
        </div>
      </SupportBannerProviderBoundary>
    </main>
  );
}

export default SearchPage;
