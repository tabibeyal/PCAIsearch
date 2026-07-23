// The Passages tab/view was removed (#143). Stale `view=results` (and any
// other `view=` value) lingers in bookmarks, shared links, and search indexes. (#147)
export function staleViewRedirectTarget(
  view: string | string[] | undefined,
  nikayas: string[],
  encodedQuery: string,
): string | null {
  if (view === undefined) return null;
  const params = new URLSearchParams();
  nikayas.forEach((n) => params.append('nikayas', n));
  const qs = params.toString();
  return `/search/${encodedQuery}${qs ? `?${qs}` : ''}`;
}