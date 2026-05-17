import React from 'react';
import { SearchBar } from '@/components/search/SearchBar';

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-[#faf9f7] text-[#2c1f14]">
      <div className="text-center mb-12">
        <h1 className="text-3xl sm:text-4xl font-serif font-bold mb-4">Ask the Pali Canon</h1>
        <p className="text-[#9c8c7a] max-w-xl mx-auto">
          Type a question or topic — find the suttas that answer it.
        </p>
      </div>
      <SearchBar />
    </div>
  );
}
