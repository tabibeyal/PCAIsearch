const BASE = 'https://www.dhammatalks.org/suttas';

export function dhammatalksUrl(id: string): string {
  const suttaRef = id.split(':')[0].trim();
  const spaceIdx = suttaRef.indexOf(' ');
  if (spaceIdx === -1) return 'https://www.dhammatalks.org';

  const prefix = suttaRef.slice(0, spaceIdx).toUpperCase();
  const num = suttaRef.slice(spaceIdx + 1);
  const numU = num.replace('.', '_');

  switch (prefix) {
    case 'DN':   return `${BASE}/DN/DN${num}.html`;
    case 'MN':   return `${BASE}/MN/MN${num}.html`;
    case 'SN':   return `${BASE}/SN/SN${numU}.html`;
    case 'AN':   return `${BASE}/AN/AN${numU}.html`;
    case 'DHP':  return `${BASE}/KN/Dhp/Ch${num}.html`;
    case 'ITI':  return `${BASE}/KN/Iti/iti${num}.html`;
    case 'UD':   return `${BASE}/KN/Ud/ud${numU}.html`;
    case 'STNP': return `${BASE}/KN/StNp/StNp${numU}.html`;
    case 'THAG': return `${BASE}/KN/Thag/thag${numU}.html`;
    case 'THIG': return `${BASE}/KN/Thig/thig${numU}.html`;
    case 'KHP':  return `${BASE}/KN/Khp/khp${num}.html`;
    default:     return 'https://www.dhammatalks.org';
  }
}
