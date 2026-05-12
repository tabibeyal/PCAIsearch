export function suttaCentralUrl(id: string): string {
  const suttaRef = id.split(':')[0].replace(/\s+/g, '').toLowerCase();
  return `https://suttacentral.net/${suttaRef}`;
}
