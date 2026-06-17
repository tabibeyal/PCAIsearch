'use client';

import React, { useState, useSyncExternalStore } from 'react';
import { useSupportBanner } from './SupportBannerContext';
import { ContactModal } from './ContactModal';

function useIsDesktop() {
  return useSyncExternalStore(
    (callback) => {
      if (typeof window === 'undefined') return () => {};
      const onResize = () => callback();
      window.addEventListener('resize', onResize);
      return () => window.removeEventListener('resize', onResize);
    },
    () => typeof window !== 'undefined' && window.innerWidth >= 768,
    () => false,
  );
}

export function SupportBanner() {
  const [visible, setVisible] = useState(false);
  const [contactOpen, setContactOpen] = useState(false);
  const { deepDiveOpen } = useSupportBanner();
  const isDesktop = useIsDesktop();

  // On mobile: show when the sentinel below FeedbackBar scrolls into view,
  // hide when it scrolls back out. On desktop the banner is always visible.
  React.useEffect(() => {
    if (isDesktop || typeof window === 'undefined') return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (deepDiveOpen) return;
        setVisible(entries.some((e) => e.isIntersecting));
      },
      { threshold: 0 }
    );

    const attach = () =>
      document.querySelectorAll('[data-support-trigger]').forEach((el) => observer.observe(el));

    attach();

    // Re-attach when sentinels mount after initial render (route changes, lazy
    // content). Coalesce with rAF so a burst of mutations — e.g. answer text
    // streaming in token by token — triggers at most one querySelectorAll per
    // frame instead of one per token.
    let rafId = 0;
    const scheduleAttach = () => {
      if (rafId) return;
      rafId = requestAnimationFrame(() => { rafId = 0; attach(); });
    };
    const mo = new MutationObserver(scheduleAttach);
    mo.observe(document.body, { childList: true, subtree: true });

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      observer.disconnect();
      mo.disconnect();
    };
  }, [deepDiveOpen, isDesktop]);

  const showBanner = (isDesktop || visible) && !deepDiveOpen;

  return (
    <>
      {contactOpen && <ContactModal onClose={() => setContactOpen(false)} />}
      <footer
        className={[
          'w-full bg-white border-t border-[#e8e4dc] py-4',
          // Mobile: fixed at bottom, slide in/out
          'fixed bottom-0 left-0 right-0 z-50 transition-transform duration-300',
          // Desktop: normal flow, always visible
          'md:static md:transform-none',
          showBanner ? 'translate-y-0' : 'translate-y-full',
        ].join(' ')}
        style={{ transitionTimingFunction: 'cubic-bezier(0, 0, 0.2, 1)' }}
      >
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 px-6 text-sm text-[#9c8c7a]">
          <p className="text-center sm:text-left">
            This tool runs on a free AI model, but server hosting still costs money.
            If this tool is useful to you, consider supporting it.
          </p>
          <div className="flex items-center gap-2 shrink-0">
            <a
              href="https://paypal.me/EyalTabib50"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-md bg-amber-500 hover:bg-amber-600 text-white font-medium px-4 py-2 transition-colors"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-4 h-4"
              >
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
              </svg>
              Support this project
            </a>
            <button
              onClick={() => setContactOpen(true)}
              className="inline-flex items-center rounded-md border border-[#e8e4dc] bg-white hover:bg-[#ede8df] text-[#6b4e35] font-medium px-4 py-2 transition-colors"
            >
              Contact
            </button>
          </div>
        </div>
      </footer>
    </>
  );
}
