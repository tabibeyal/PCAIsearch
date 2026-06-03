'use client';
import dynamic from 'next/dynamic';

const SearchBarDynamic = dynamic(
  () => import('./SearchBar').then(m => ({ default: m.SearchBar })),
  { ssr: false }
);

export function SearchBarClient() {
  return <SearchBarDynamic />;
}
