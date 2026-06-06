'use client';

import React from 'react';
import { SynthesisView } from './SynthesisView';
import { SourceViewer } from './SourceViewer';
import { DividerToggle } from './DividerToggle';
import { SynthesisResponse } from '@/types/api';
import { useSupportBanner } from '@/components/SupportBannerContext';

interface DualPaneContainerProps {
  data: SynthesisResponse;
}

export function DualPaneContainer({ data }: DualPaneContainerProps) {
  const [deepDive, setDeepDive] = React.useState(false);
  const [sourcesVisible, setSourcesVisible] = React.useState(true);
  const [activeRef, setActiveRef] = React.useState<string | undefined>(undefined);
  const { setDeepDiveOpen } = useSupportBanner();

  const handleCitationClick = (ref: string) => {
    setActiveRef(ref);
    if (!deepDive) setDeepDive(true);
    setSourcesVisible(true); // always reopen sources when jumping to a citation
    const id = `verse-${ref.replace(/\s+/g, '-').toLowerCase()}`;
    setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 50);
  };

  const handleDeepDiveToggle = () => {
    if (!deepDive) {
      setDeepDive(true);
    } else {
      setSourcesVisible((v) => !v);
    }
  };

  const showSources = deepDive && sourcesVisible;

  React.useEffect(() => {
    setDeepDiveOpen(deepDive);
  }, [deepDive, setDeepDiveOpen]);

  React.useEffect(() => {
    if (!showSources || !activeRef) return;
    const id = `verse-${activeRef.replace(/\s+/g, '-').toLowerCase()}`;
    setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 50);
  }, [showSources]);

  return (
    <div className={`relative flex h-full w-full overflow-hidden bg-gray-200 ${deepDive ? 'flex-col md:flex-row' : ''}`}>
      <div className={`overflow-hidden shadow-xl transition-all duration-300 ${
        deepDive
          ? showSources
            ? 'w-full md:w-1/2 h-1/2 md:h-full border-b border-gray-300 md:border-b-0 md:border-r'
            : 'w-full h-full'
          : 'w-full h-full'
      }`}>
        <SynthesisView
          data={data}
          deepDive={deepDive}
          sourcesVisible={sourcesVisible}
          onDeepDiveToggle={handleDeepDiveToggle}
          onCitationClick={handleCitationClick}
        />
      </div>

      {deepDive && (
        <div key={String(deepDive)} style={{ animation: 'fadeIn 150ms ease forwards' }}>
          <DividerToggle
            sourcesVisible={sourcesVisible}
            onClick={() => setSourcesVisible((v) => !v)}
          />
        </div>
      )}

      {showSources && (
        <div
          className="w-full md:w-1/2 h-1/2 md:h-full overflow-hidden"
          style={{ animation: 'paneEnter 300ms cubic-bezier(0.22, 1, 0.36, 1) forwards' }}
        >
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
