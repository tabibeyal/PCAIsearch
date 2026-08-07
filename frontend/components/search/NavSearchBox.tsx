'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';

export function NavSearchBox({ initialQuery }: { initialQuery: string }) {
  const [q, setQ] = useState(initialQuery);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  function navigate() {
    const trimmed = q.trim();
    if (!trimmed) return;
    setIsLoading(true);
    router.push(`/search/${encodeURIComponent(trimmed)}`);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') navigate();
  }

  return (
    <div className="flex flex-1 min-w-0 items-center bg-white border border-[#e8e4dc] rounded-2xl px-4 py-2 focus-within:border-[#9c8c7a] focus-within:ring-2 focus-within:ring-[#9c8c7a] transition-colors">
      <input
        type="text"
        value={q}
        onChange={e => setQ(e.target.value)}
        onKeyDown={handleKeyDown}
        aria-label="Ask again"
        placeholder="Ask again…"
        className="flex-1 min-w-0 bg-transparent text-sm text-[#2c1f14] placeholder-[#76604a] outline-none"
      />
      <button
        onClick={navigate}
        disabled={!q.trim()}
        className={`ml-2 w-9 h-9 flex items-center justify-center rounded-lg text-white disabled:opacity-25 transition-all active:scale-95 shrink-0 ${isLoading ? 'bg-[#9c8c7a]' : 'bg-[#4a3728] hover:bg-[#6b4e35]'}`}
        title="Submit"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"/>
          <polyline points="5 12 12 5 19 12"/>
        </svg>
      </button>
    </div>
  );
}
