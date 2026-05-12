import React from 'react';
import { SearchBar } from '@/components/search/SearchBar';

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-gray-50 text-black">
      <div className="text-center mb-12">
        <h1 className="text-3xl sm:text-4xl font-serif font-bold mb-4">Ask the Pali Canon</h1>
        <p className="text-gray-600 max-w-xl mx-auto">
          Type a question or topic — find the suttas that answer it.
        </p>
      </div>
      <SearchBar />
    </div>
  );
}
