'use client';

import React, { useEffect, useRef, useState } from 'react';

const PROMPTS = [
  'what were the Buddha\'s last words before he died?',
  'why does loving someone lead to grief and suffering?',
  'should a monk feel anger even if attacked with a saw?',
  'is having a good spiritual friend the whole of the holy life?',
  'what is the path between self-indulgence and harsh self-denial?',
  'how should one treat parents family and friends according to the Buddha?',
  'what did the Buddha consider after enlightenment before deciding to teach?',
];

const TYPE_MS = 55;
const DELETE_MS = 22;
const HOLD_MS = 2000;
const PAUSE_MS = 350;

export function SearchBar() {
  const [query, setQuery] = useState('');
  const [animText, setAnimText] = useState('');
  const [cursorOn, setCursorOn] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [focused, setFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { setMounted(true); }, []);

  // cursor blink
  useEffect(() => {
    const id = setInterval(() => setCursorOn(v => !v), 530);
    return () => clearInterval(id);
  }, []);

  // typing animation — pauses while the box is focused
  useEffect(() => {
    if (focused) return;

    let cancelled = false;

    const delay = (ms: number) =>
      new Promise<void>(resolve => setTimeout(resolve, ms));

    async function run() {
      let idx = 0;
      while (!cancelled) {
        const prompt = PROMPTS[idx % PROMPTS.length];

        for (let i = 1; i <= prompt.length; i++) {
          if (cancelled) return;
          setAnimText(prompt.slice(0, i));
          await delay(TYPE_MS);
        }

        await delay(HOLD_MS);
        if (cancelled) return;

        for (let i = prompt.length - 1; i >= 0; i--) {
          if (cancelled) return;
          setAnimText(prompt.slice(0, i));
          await delay(DELETE_MS);
        }

        await delay(PAUSE_MS);
        idx++;
      }
    }

    run();
    return () => { cancelled = true; };
  }, [focused]);

  function autoResize(el: HTMLTextAreaElement) {
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const q = query.trim();
    if (!q) return;
    window.location.href = `/search/${encodeURIComponent(q)}`;
  }

  const showAnim = query === '' && !focused;
  const [animMounted, setAnimMounted] = useState(true);

  useEffect(() => {
    if (!showAnim) {
      const t = setTimeout(() => setAnimMounted(false), 200);
      return () => clearTimeout(t);
    }
    setAnimMounted(true);
  }, [showAnim]);

  return (
    <div className="w-full max-w-2xl mx-auto relative rounded-2xl border border-[#e8e4dc] bg-white px-4 pt-4 pb-14 focus-within:border-[#9c8c7a] focus-within:ring-2 focus-within:ring-[#e8e4dc] transition-all shadow-sm">

      {/* Fix 5: animated placeholder fades out on first keystroke */}
      {mounted && animMounted && (
        <div
          className="absolute top-4 left-4 right-14 text-base leading-relaxed text-[#b5a494] pointer-events-none select-none"
          aria-hidden="true"
          style={{
            opacity: showAnim ? 1 : 0,
            transform: showAnim ? 'translateY(0)' : 'translateY(-4px)',
            transition: 'opacity 200ms ease, transform 200ms ease',
          }}
        >
          {animText}
          <span
            className="inline-block w-px h-[1.1em] bg-[#b5a494] align-middle ml-px"
            style={{ opacity: cursorOn ? 1 : 0, transition: 'opacity 0.1s' }}
          />
        </div>
      )}

      <textarea
        ref={textareaRef}
        rows={1}
        value={query}
        onChange={(e) => { setQuery(e.target.value); autoResize(e.target); }}
        onKeyDown={handleKeyDown}
        onFocus={() => { setFocused(true); setAnimText(''); }}
        onBlur={() => setFocused(false)}
        placeholder=""
        className="w-full bg-transparent resize-none outline-none text-[#2c1f14] text-base leading-relaxed max-h-64 overflow-y-auto relative z-10"
        style={{ minHeight: '28px', caretColor: focused || query !== '' ? '#b5a494' : 'transparent' }}
      />

      <button
        onClick={submit}
        disabled={!query.trim()}
        className="absolute bottom-3 right-3 w-9 h-9 flex items-center justify-center rounded-xl bg-[#4a3728] text-white disabled:opacity-25 hover:bg-[#6b4e35] transition-all"
        title="Submit"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"/>
          <polyline points="5 12 12 5 19 12"/>
        </svg>
      </button>
    </div>
  );
}
