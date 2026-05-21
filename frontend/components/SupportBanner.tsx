'use client';

import React, { useState, useEffect, useRef } from 'react';

export function SupportBanner() {
  const [visible, setVisible] = useState(false);
  const footerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const isMobile = () => window.innerWidth < 768;
    let lastScrollTop = 0;

    const handleScroll = (e: Event) => {
      if (!isMobile()) return;
      const target = e.target as Element;
      if (!(target instanceof Element) || target.clientHeight < 200) return;

      const scrollTop = target.scrollTop;
      const atBottom = target.scrollHeight - scrollTop - target.clientHeight < 80;
      const scrollingUp = scrollTop < lastScrollTop;
      lastScrollTop = scrollTop;

      if (atBottom) {
        setVisible(true);
      } else if (scrollingUp) {
        setVisible(false);
      }
    };

    document.addEventListener('scroll', handleScroll, { capture: true, passive: true });
    return () => document.removeEventListener('scroll', handleScroll, true);
  }, []);

  // Keep scroll containers padded so content isn't hidden behind the fixed banner
  useEffect(() => {
    if (typeof window === 'undefined' || window.innerWidth >= 768) return;
    const h = footerRef.current?.offsetHeight ?? 0;
    document.documentElement.style.setProperty('--banner-h', visible ? `${h}px` : '0px');
    if (visible) {
      document.documentElement.setAttribute('data-banner-open', '');
    } else {
      document.documentElement.removeAttribute('data-banner-open');
    }
  }, [visible]);

  return (
    <footer
      ref={footerRef}
      className={[
        'w-full bg-white border-t border-gray-200 py-4',
        // Mobile: fixed at bottom, slide in/out
        'fixed bottom-0 left-0 right-0 z-50 transition-transform duration-300',
        // Desktop: back to normal flow, always visible
        'md:static md:transform-none',
        visible ? 'translate-y-0' : 'translate-y-full',
      ].join(' ')}
    >
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 px-6 text-sm text-gray-500">
        <p className="text-center sm:text-left">
          This tool runs on a free AI model, but hosting and infrastructure still cost money.
          If this tool is useful to you, consider supporting it.
        </p>
        <a
          href="https://paypal.me/EyalTabib50"
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 inline-flex items-center gap-2 rounded-md bg-amber-500 hover:bg-amber-600 text-white font-medium px-4 py-2 transition-colors"
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
      </div>
    </footer>
  );
}
