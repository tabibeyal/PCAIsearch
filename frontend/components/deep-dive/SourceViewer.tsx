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
          context.map((verse) => (
            <div
              key={verse.id}
              id={`verse-${verse.id.replace(/\s+/g, '-').toLowerCase()}`}
              className={`scroll-mt-4 p-4 rounded-lg transition-all duration-300 border ${
                activeRef === verse.id
                  ? 'bg-[#ede8df] border-[#c8b89a]'
                  : 'bg-white border-[#e8e4dc]'
              }`}
            >
              <div className="text-xs font-semibold mb-2">
                <a
                  href={dhammatalksUrl(verse.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#6b4e35] hover:underline"
                >
                  {verse.id}
                </a>
              </div>
              <div className="mb-3 text-base leading-relaxed italic text-[#76604a]">
                {verse.pali}
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
          ))
        )}
      </div>
    </div>
  );
}
