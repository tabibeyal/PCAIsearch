'use client';

import React from 'react';
import { useRouter } from 'next/navigation';

// DN/MN/SN/AN are the four main nikāyas. The rest are Khuddaka-pāṭha
// sub-books; grouping them behind a disclosure keeps the filter row to a
// scannable five choices (All + four nikāyas) instead of twelve peer pills.
const MAIN_NIKAYAS = ['DN', 'MN', 'SN', 'AN'];
const KHUDDAKA = ['DHP', 'ITI', 'UD', 'STNP', 'THAG', 'THIG', 'KHP'];

interface NikayaFilterProps {
  encodedQuery: string;
  view: string;
  selected: string[];
}

export function NikayaFilter({ encodedQuery, view, selected }: NikayaFilterProps) {
  const router = useRouter();
  const isAll = selected.length === 0;
  const [modKey, setModKey] = React.useState('⌘/Ctrl');
  const [pending, setPending] = React.useState<string | null>(null);
  const activeKhuddaka = selected.filter(n => KHUDDAKA.includes(n));
  // Open by default when a Khuddaka book is already in the URL selection.
  const [khuddakaOpen, setKhuddakaOpen] = React.useState(() => activeKhuddaka.length > 0);

  React.useEffect(() => {
    const t = setTimeout(() => setModKey(/Mac|iPhone|iPad|iPod/.test(navigator.platform) ? '⌘' : 'Ctrl'), 0);
    return () => clearTimeout(t);
  }, []);

  // Reopen the disclosure when a Khuddaka book becomes selected (e.g. via a
  // filtered URL), so the active sub-book stays visible. Closing is still
  // allowed; the group button shows a count while a sub-book is active.
  React.useEffect(() => {
    if (activeKhuddaka.length > 0) setKhuddakaOpen(true);
  }, [activeKhuddaka.length]);

  function navigate(next: string[]) {
    const params = new URLSearchParams({ view });
    next.forEach(n => params.append('nikayas', n));
    router.push(`/search/${encodedQuery}?${params}`);
  }

  function handlePillClick(nikaya: string, e: React.MouseEvent) {
    setPending(nikaya);
    const addMode = e.metaKey || e.ctrlKey;
    if (addMode) {
      // Cmd/Ctrl+click: toggle this nikaya in/out of the selection
      if (selected.includes(nikaya)) {
        navigate(selected.filter(n => n !== nikaya));
      } else {
        navigate([...selected, nikaya]);
      }
    } else {
      // Plain click: switch to this nikaya only
      if (selected.length === 1 && selected[0] === nikaya) {
        navigate([]); // clicking the sole active pill resets to All
      } else {
        navigate([nikaya]);
      }
    }
  }

  const pillClass = (active: boolean, key: string) =>
    `px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer border active:scale-95 ${
      pending === key
        ? 'bg-[#d4c9b8] text-[#4a3728] border-[#c8bca8]'
        : active
          ? 'bg-[#ede8df] text-[#6b4e35] border-[#e8e4dc]'
          : 'border-[#e8e4dc] text-[#76604a] hover:bg-[#ede8df]'
    }`;

  const khuddakaActive = activeKhuddaka.length > 0;
  const khuddakaBtnClass = `px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer border inline-flex items-center gap-1 active:scale-95 ${
    khuddakaOpen || khuddakaActive
      ? 'bg-[#ede8df] text-[#6b4e35] border-[#e8e4dc]'
      : 'border-[#e8e4dc] text-[#76604a] hover:bg-[#ede8df]'
  }`;

  return (
    <div className="flex gap-2 items-center flex-wrap">
      <span className="text-xs text-[#76604a] font-medium">
        Nikāya:
      </span>
      <span className="hidden sm:inline text-[10px] text-[#76604a] -ml-1">
        ({modKey}-click to add)
      </span>
      <button className={pillClass(isAll, 'All')} onClick={() => { setPending('All'); navigate([]); }}>
        All
      </button>
      {MAIN_NIKAYAS.map(n => (
        <button key={n} className={pillClass(selected.includes(n), n)} onClick={e => handlePillClick(n, e)}>
          {n}
        </button>
      ))}
      <button
        type="button"
        className={khuddakaBtnClass}
        onClick={() => setKhuddakaOpen(o => !o)}
        aria-expanded={khuddakaOpen}
        aria-controls="khuddaka-books"
      >
        Khuddaka
        {khuddakaActive && <span className="text-[10px] tabular-nums">({activeKhuddaka.length})</span>}
        <span className={`inline-block transition-transform duration-200 ${khuddakaOpen ? 'rotate-180' : ''}`} aria-hidden="true">▾</span>
      </button>
      {khuddakaOpen && (
        <span id="khuddaka-books" className="flex flex-wrap gap-2 items-center">
          {KHUDDAKA.map(n => (
            <button key={n} className={pillClass(selected.includes(n), n)} onClick={e => handlePillClick(n, e)}>
              {n}
            </button>
          ))}
        </span>
      )}
    </div>
  );
}