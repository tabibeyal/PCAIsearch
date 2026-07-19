const BASE = 'https://www.dhammatalks.org/suttas';

// The book code (DN, MN, DHP, …) is the first whitespace-delimited token of the
// id's "<book> <num>:<verse>" prefix. Empty when the id has no space — callers
// treat that as "no known book" (dhammatalksUrl falls back to the home page).
export function bookCodeFromId(id: string): string {
  const suttaRef = id.split(':')[0].trim();
  const spaceIdx = suttaRef.indexOf(' ');
  return spaceIdx === -1 ? '' : suttaRef.slice(0, spaceIdx).toUpperCase();
}

export function dhammatalksUrl(id: string): string {
  const prefix = bookCodeFromId(id);
  if (!prefix) return 'https://www.dhammatalks.org';

  const suttaRef = id.split(':')[0].trim();
  const num = suttaRef.slice(suttaRef.indexOf(' ') + 1);
  const numU = num.replace('.', '_');

  switch (prefix) {
    case 'DN':   return `${BASE}/DN/DN${num.padStart(2, '0')}.html`;
    case 'MN':   return `${BASE}/MN/MN${num}.html`;
    case 'SN':   return `${BASE}/SN/SN${numU}.html`;
    case 'AN':   return `${BASE}/AN/AN${numU}.html`;
    case 'DHP':  return `${BASE}/KN/Dhp/Ch${num.padStart(2, '0')}.html`;
    case 'ITI':  return `${BASE}/KN/Iti/iti${num}.html`;
    case 'UD':   return `${BASE}/KN/Ud/ud${numU}.html`;
    case 'STNP': return `${BASE}/KN/StNp/StNp${numU}.html`;
    case 'THAG': return `${BASE}/KN/Thag/thag${numU}.html`;
    case 'THIG': return `${BASE}/KN/Thig/thig${numU}.html`;
    case 'KHP':  return `${BASE}/KN/Khp/khp${num}.html`;
    default:     return 'https://www.dhammatalks.org';
  }
}
