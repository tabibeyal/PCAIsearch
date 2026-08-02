// Trim a question to fit the OG banner's 2-line example slot.
// When truncated, append an ellipsis to signal the cut. Single source of
// truth for the home + share banners so they stay consistent.

const MAX_LENGTH = 100;

export function formatQuestionForBanner(text: string): string {
  const trimmed = text.trim();
  if (trimmed.length <= MAX_LENGTH) return trimmed;
  return `${trimmed.slice(0, MAX_LENGTH).trimEnd()}…`;
}
