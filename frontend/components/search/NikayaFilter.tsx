'use client';

import React from 'react';
import { useRouter } from 'next/navigation';

const ALL_NIKAYAS = ['DN', 'MN', 'SN', 'AN', 'DHP', 'ITI'];

interface NikayaFilterProps {
  encodedQuery: string;
  view: string;
  selected: string[];
}

export function NikayaFilter({ encodedQuery, view, selected }: NikayaFilterProps) {
  const router = useRouter();
  const isAll = selected.length === 0;
  const [modKey, setModKey] = React.useState('⌘/Ctrl');

  React.useEffect(() => {
    setModKey(/Mac|iPhone|iPad|iPod/.test(navigator.platform) ? '⌘' : 'Ctrl');
  }, []);

  function navigate(next: string[]) {
    const params = new URLSearchParams({ view });
    next.forEach(n => params.append('nikayas', n));
    router.push(`/search/${encodedQuery}?${params}`);
  }

  function handlePillClick(nikaya: string, e: React.MouseEvent) {
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

  const pillClass = (active: boolean) =>
    `px-3 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer border ${
      active
        ? 'bg-[#ede8df] text-[#6b4e35] border-[#e8e4dc]'
        : 'border-[#e8e4dc] text-[#9c8c7a] hover:bg-[#ede8df]'
    }`;

  return (
    <div className="flex gap-2 items-center flex-wrap">
      <span
        className="text-xs text-[#9c8c7a] font-medium cursor-help"
        title={`Click to switch · ${modKey}-click to add`}
      >
        Nikāya:
      </span>
      <button className={pillClass(isAll)} onClick={() => navigate([])}>
        All
      </button>
      {ALL_NIKAYAS.map(n => (
        <button key={n} className={pillClass(selected.includes(n))} onClick={e => handlePillClick(n, e)}>
          {n}
        </button>
      ))}
    </div>
  );
}
