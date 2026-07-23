import React from 'react';
import Link from 'next/link';
import { SynthesisLoader } from '@/components/deep-dive/SynthesisLoader';
import { NikayaFilter } from '@/components/search/NikayaFilter';
import { NavSearchBox } from '@/components/search/NavSearchBox';
import { SupportBanner } from '@/components/SupportBanner';
import { SupportBannerProvider } from '@/components/SupportBannerContext';

async function SearchPage({
  params,
  searchParams,
}: {
  params: Promise<{ query: string }>;
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const { query: rawQuery } = await params;
  const { nikayas: nikayasParam } = await searchParams;
  const query = decodeURIComponent(rawQuery);
  const encodedQuery = encodeURIComponent(query);
  const nikayas = Array.isArray(nikayasParam)
    ? nikayasParam
    : nikayasParam
    ? [nikayasParam]
    : [];

  return (
    <main className="h-full w-full">
      <SupportBannerProvider>
        <div className="flex flex-col h-full">
          <nav className="bg-[#faf9f7] border-b border-[#e8e4dc] sticky top-0 z-10">
            {/* Row 1: brand + search */}
            <div className="flex items-center gap-3 px-3 sm:px-4 pt-3 pb-2">
              <Link href="/" className="text-sm text-[#76604a] hover:text-[#6b4e35] whitespace-nowrap transition-colors">
                Home
              </Link>
              <NavSearchBox key={query} initialQuery={query} />
            </div>
            {/* Row 2: filter */}
            <div className="flex items-center gap-2 px-3 sm:px-4 pb-3 flex-wrap">
              <NikayaFilter encodedQuery={encodedQuery} selected={nikayas} />
            </div>
          </nav>
          <div className="flex-1 min-h-0 overflow-auto">
            <SynthesisLoader query={query} nikayas={nikayas} />
          </div>
          <SupportBanner />
        </div>
      </SupportBannerProvider>
    </main>
  );
}

export default SearchPage;
