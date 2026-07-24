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
  };

  const handleDeepDiveToggle = () => {
    if (deepDive) {
      setDeepDive(false);
      setSourcesVisible(true);
    } else {
      setDeepDive(true);
    }
  };

  const showSources = deepDive && sourcesVisible;

  React.useEffect(() => {
    setDeepDiveOpen(deepDive);
  }, [deepDive, setDeepDiveOpen]);

  // Scroll the cited verse to the top of the sources pane. Single source of truth: the
  // click handler used to fire its own smooth scroll too, and the two competing smooth
  // scrolls cancelled each other mid-flight, halting partway down the card with the verse
  // title scrolled out of view. rAF waits for the pane to commit before scrolling once.
  React.useEffect(() => {
    if (!showSources || !activeRef) return;
    const id = `verse-${activeRef.replace(/\s+/g, '-').toLowerCase()}`;
    let cancelled = false;
    const raf = requestAnimationFrame(() => {
      if (cancelled) return;
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    return () => { cancelled = true; cancelAnimationFrame(raf); };
  }, [showSources, activeRef]);

  return (
    <div className={`relative flex h-full w-full overflow-hidden bg-[#e8e4dc] ${deepDive ? 'flex-col md:flex-row' : ''}`}>
      <div className={`overflow-hidden transition-all duration-300 ${
        deepDive
          ? showSources
            ? 'w-full md:w-1/2 h-[54%] md:h-full border-b border-[#e8e4dc] md:border-b-0 md:border-r'
            : 'w-full h-full'
          : 'w-full h-full'
      }`}>
        <SynthesisView
          data={data}
          deepDive={deepDive}
          onDeepDiveToggle={handleDeepDiveToggle}
          onCitationClick={handleCitationClick}
        />
      </div>

      {deepDive && (
        <div
          key={String(deepDive)}
          style={{ position: 'absolute', inset: 0, zIndex: 20, pointerEvents: 'none', animation: 'fadeIn 150ms ease forwards' }}
        >
          <DividerToggle
            sourcesVisible={sourcesVisible}
            onClick={() => {
              if (sourcesVisible) {
                setDeepDive(false);
                setSourcesVisible(true);
              } else {
                setSourcesVisible(true);
              }
            }}
          />
        </div>
      )}

      {showSources && (
        <div
          className="w-full md:w-1/2 h-[46%] md:h-full overflow-hidden"
          style={{ animation: 'paneEnter 300ms cubic-bezier(0.22, 1, 0.36, 1) forwards' }}
        >
          <SourceViewer
            context={data.context}
            activeRef={activeRef}
            onClose={handleDeepDiveToggle}
          />
        </div>
      )}
    </div>
  );
}
