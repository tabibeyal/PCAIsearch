export function suttaCentralUrl(id: string): string {
  const normalized = id.toLowerCase().replace(/\s+/g, '');
  return `https://suttacentral.net/${normalized}`;
}
