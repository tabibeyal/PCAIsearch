import React from 'react';
import { SearchBar } from '@/components/search/SearchBar';

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-gray-50 text-black">
      <div className="text-center mb-12">
        <h1 className="text-3xl sm:text-4xl font-serif font-bold mb-4">Pali Canon AI Search</h1>
        <p className="text-gray-600 max-w-xl mx-auto">
          Semantic search and synthesis across the Nikayas. High-fidelity citations
          verified by a deterministic guardrail.
        </p>
      </div>
      <SearchBar />
    </div>
  );
}
