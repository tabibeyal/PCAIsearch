'use client';

import React from 'react';
import { SynthesisView } from './SynthesisView';
import { SourceViewer } from './SourceViewer';
import { SynthesisResponse } from '@/types/api';

interface DualPaneContainerProps {
  data: SynthesisResponse;
}

export function DualPaneContainer({ data }: DualPaneContainerProps) {
  const [deepDive, setDeepDive] = React.useState(false);
  const [sourcesVisible, setSourcesVisible] = React.useState(true);
  const [activeRef, setActiveRef] = React.useState<string | undefined>(undefined);

  const handleCitationClick = (ref: string) => {
    setActiveRef(ref);
    if (!deepDive) setDeepDive(true);
    setSourcesVisible(true);
    const id = `verse-${ref.replace(/\s+/g, '-').toLowerCase()}`;
    setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 50);
  };

  return (
    <div className={`flex h-screen w-full overflow-hidden bg-gray-200 ${deepDive ? 'flex-col md:flex-row' : ''}`}>
      <div className={`h-full border-r border-gray-300 shadow-xl overflow-hidden transition-all duration-300 ${
        deepDive ? 'w-full md:w-1/2 h-1/2 md:h-full' : 'w-full h-full'
      }`}>
        <SynthesisView
          data={data}
          deepDive={deepDive}
          onDeepDiveToggle={() => setDeepDive((v) => !v)}
          onCitationClick={handleCitationClick}
        />
      </div>

      {deepDive && sourcesVisible && (
        <div className="w-full md:w-1/2 h-1/2 md:h-full overflow-hidden">
          <SourceViewer
            context={data.context}
            activeRef={activeRef}
            onClose={() => setSourcesVisible(false)}
          />
        </div>
      )}
    </div>
  );
}
