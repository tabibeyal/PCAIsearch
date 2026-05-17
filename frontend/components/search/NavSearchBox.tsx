'use client';

import React, { useState } from 'react';

export function NavSearchBox({ initialQuery }: { initialQuery: string }) {
  const [q, setQ] = useState(initialQuery);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      const trimmed = q.trim();
      if (trimmed) window.location.href = `/search/${encodeURIComponent(trimmed)}`;
    }
  }

  return (
    <input
      type="text"
      value={q}
      onChange={e => setQ(e.target.value)}
      onKeyDown={handleKeyDown}
      className="flex-1 min-w-0 bg-white border border-[#e8e4dc] rounded-2xl px-4 py-2 text-sm text-[#2c1f14] placeholder-[#9c8c7a] focus:outline-none focus:border-[#9c8c7a]"
    />
  );
}
