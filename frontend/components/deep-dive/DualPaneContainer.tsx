import React from 'react';
import { SynthesisView } from './SynthesisView';
import { SourceViewer } from './SourceViewer';
import { SynthesisResponse } from '@/types/api';

interface DualPaneContainerProps {
  data: SynthesisResponse;
}

export function DualPaneContainer({ data }: DualPaneContainerProps) {
  const [deepDive, setDeepDive] = React.useState(false);
  const [activeRef, setActiveRef] = React.useState<string | undefined>(undefined);

  const handleCitationClick = (ref: string) => {
    setActiveRef(ref);
    if (!deepDive) setDeepDive(true);
    const id = `verse-${ref.replace(/\s+/g, '-').toLowerCase()}`;
    setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 50);
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-gray-200">
      <div className={`h-full border-r border-gray-300 shadow-xl overflow-hidden transition-all duration-300 ${deepDive ? 'w-1/2' : 'w-full'}`}>
        <SynthesisView
          data={data}
          deepDive={deepDive}
          onDeepDiveToggle={() => setDeepDive((v) => !v)}
          onCitationClick={handleCitationClick}
        />
      </div>

      {deepDive && (
        <div className="w-1/2 h-full overflow-hidden">
          <SourceViewer context={data.context} activeRef={activeRef} />
        </div>
      )}
    </div>
  );
}
