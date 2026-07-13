import { SearchResult } from '@/types/api';
import { dhammatalksUrl } from '@/lib/sourceUrl';

interface SourceViewerProps {
  context: SearchResult[];
  activeRef?: string;
  onClose?: () => void;
}

export function SourceViewer({ context, activeRef, onClose }: SourceViewerProps) {
  return (
    <div className="h-full flex flex-col">
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="md:hidden flex-shrink-0 w-full flex items-center justify-center gap-2 py-2.5 bg-[#faf9f7] border-b-[1.5px] border-[#6b4e35] text-[#6b4e35] text-xs font-semibold"
          aria-label="Hide sources"
        >
          Sources <span className="text-sm leading-none">▾</span>
        </button>
      )}
      <div className="flex-1 overflow-y-auto scroll-smooth p-6 space-y-8 font-serif text-[#2c1f14] bg-[#faf9f7]">
        {context.length === 0 ? (
          <div className="text-[#76604a] italic">No source verses found.</div>
        ) : (
          context.map((verse) => {
            const hasTitle = Boolean(verse.title_english || verse.title_pali);
            return (
            <div
              key={verse.id}
              id={`verse-${verse.id.replace(/\s+/g, '-').toLowerCase()}`}
              className={`scroll-mt-4 p-4 rounded-lg transition-all duration-300 border ${
                activeRef === verse.id
                  ? 'bg-[#ede8df] border-[#c8b89a]'
                  : 'bg-white border-[#e8e4dc]'
              }`}
            >
              {hasTitle && (
                <div className="mb-2">
                  {verse.title_english && (
                    <div className="text-base font-semibold text-[#2c1f14]">
                      {verse.title_english}
                    </div>
                  )}
                  {verse.title_pali && (
                    <div className="text-sm italic text-[#76604a]">
                      {verse.title_pali}
                    </div>
                  )}
                </div>
              )}
              <div className="mb-2">
                {/* Badge under a title; plain small link when there is none (#85).
                    Border keeps the pill visible on the active card, whose bg matches the pill's. */}
                <a
                  href={dhammatalksUrl(verse.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={
                    hasTitle
                      ? 'inline-block bg-[#ede8df] border border-[#d4c4a8] text-[#6b4e35] text-xs font-medium px-2 py-0.5 rounded hover:underline'
                      : 'text-[#6b4e35] text-xs font-semibold hover:underline'
                  }
                >
                  {verse.id}
                </a>
              </div>
              {verse.passage ? (
                <div className="space-y-2 text-[15px] leading-[1.75]">
                  {verse.passage.map((line) => (
                    <p
                      key={line.id}
                      className={line.isMatch ? 'text-[#2c1f14]' : 'text-[#76604a]'}
                    >
                      {line.english}
                    </p>
                  ))}
                </div>
              ) : (
                <div className="text-[15px] leading-[1.75] text-[#2c1f14]">
                  {verse.english}
                </div>
              )}
            </div>
            );
          })
        )}
      </div>
    </div>
  );
}
