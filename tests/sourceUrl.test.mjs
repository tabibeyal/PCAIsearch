/**
 * Verification script for sourceUrl link generation.
 * Run: node tests/sourceUrl.test.mjs
 *
 * Mirrors the logic in frontend/lib/sourceUrl.ts so it can run without a bundler.
 */

const BASE = 'https://www.dhammatalks.org/suttas';

function dhammatalksUrl(id) {
  const suttaRef = id.split(':')[0].trim();
  const spaceIdx = suttaRef.indexOf(' ');
  if (spaceIdx === -1) return 'https://www.dhammatalks.org';

  const prefix = suttaRef.slice(0, spaceIdx).toUpperCase();
  const num = suttaRef.slice(spaceIdx + 1);
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

const cases = [
  // DN: zero-padded (epub filenames are DN01.html, DN02.html, etc.)
  ['DN 1: 3',   `${BASE}/DN/DN01.html`],
  ['DN 9: 1',   `${BASE}/DN/DN09.html`],
  ['DN 10: 2',  `${BASE}/DN/DN10.html`],
  ['DN 34: 5',  `${BASE}/DN/DN34.html`],

  // MN: no zero-padding (epub filenames are MN1.html, MN2.html, etc.)
  ['MN 1: 3',   `${BASE}/MN/MN1.html`],
  ['MN 10: 2',  `${BASE}/MN/MN10.html`],
  ['MN 152: 4', `${BASE}/MN/MN152.html`],

  // SN: dot replaced with underscore
  ['SN 12.2: 3',  `${BASE}/SN/SN12_2.html`],
  ['SN 56.11: 1', `${BASE}/SN/SN56_11.html`],

  // AN: dot replaced with underscore
  ['AN 1.1: 2',   `${BASE}/AN/AN1_1.html`],
  ['AN 10.176: 1',`${BASE}/AN/AN10_176.html`],

  // DHP: zero-padded chapter numbers (epub filenames are Ch01.html, etc.)
  ['DHP 1: 3',   `${BASE}/KN/Dhp/Ch01.html`],
  ['DHP 9: 1',   `${BASE}/KN/Dhp/Ch09.html`],
  ['DHP 10: 2',  `${BASE}/KN/Dhp/Ch10.html`],
  ['DHP 26: 1',  `${BASE}/KN/Dhp/Ch26.html`],

  // ITI: no zero-padding
  ['ITI 1: 1',   `${BASE}/KN/Iti/iti1.html`],
  ['ITI 112: 1', `${BASE}/KN/Iti/iti112.html`],

  // UD: dot replaced with underscore
  ['UD 1.1: 2',  `${BASE}/KN/Ud/ud1_1.html`],
  ['UD 8.4: 1',  `${BASE}/KN/Ud/ud8_4.html`],

  // STNP: dot replaced with underscore
  ['STNP 1.1: 2', `${BASE}/KN/StNp/StNp1_1.html`],

  // THAG: single and compound
  ['THAG 1: 1',   `${BASE}/KN/Thag/thag1.html`],
  ['THAG 1.1: 1', `${BASE}/KN/Thag/thag1_1.html`],

  // THIG
  ['THIG 1: 1',   `${BASE}/KN/Thig/thig1.html`],

  // KHP
  ['KHP 1: 1',    `${BASE}/KN/Khp/khp1.html`],

  // Unknown nikaya → fallback
  ['XY 1: 1',     'https://www.dhammatalks.org'],
  ['bad',          'https://www.dhammatalks.org'],
];

let passed = 0;
let failed = 0;
for (const [input, expected] of cases) {
  const actual = dhammatalksUrl(input);
  if (actual === expected) {
    passed++;
  } else {
    console.error(`FAIL  dhammatalksUrl("${input}")`);
    console.error(`      expected: ${expected}`);
    console.error(`      actual:   ${actual}`);
    failed++;
  }
}

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
