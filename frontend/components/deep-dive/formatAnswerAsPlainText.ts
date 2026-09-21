import { SearchResult } from '@/types/api';

const CITATION_RE = /\[([A-Za-z\s\d:.,\-]+)\]/g;
const BOLD_RE = /\*\*([^*]+)\*\*/g;
const ITALIC_RE = /\*([^*]+)\*/g;
// citation_support_check.py's UNSUPPORTED_MARKER — plain text has no amber
// tag to carry, so it's dropped the same way bold/italic markers are below,
// leaving the real, title-lookup-able citation ID behind.
const UNSUPPORTED_SUFFIX = ' unsupported';

export function formatAnswerAsPlainText(answer: string, context: SearchResult[]): string {
  const titleById = new Map(context.map((c) => [c.id, c.title]));

  const withExpandedCitations = answer.replace(CITATION_RE, (match, refsRaw: string) => {
    const refs = refsRaw.split(',').map((r) => r.trim()).filter(Boolean);
    const expanded = refs.map((rawRef) => {
      const ref = rawRef.endsWith(UNSUPPORTED_SUFFIX)
        ? rawRef.slice(0, -UNSUPPORTED_SUFFIX.length)
        : rawRef;
      const title = titleById.get(ref);
      return title ? `${ref} — ${title}` : ref;
    });
    return `[${expanded.join(', ')}]`;
  });

  return withExpandedCitations.replace(BOLD_RE, '$1').replace(ITALIC_RE, '$1');
}
