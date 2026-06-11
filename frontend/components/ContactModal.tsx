'use client';

import React, { useEffect, useRef, useState } from 'react';
import { submitContact } from '@/lib/api';

interface ContactModalProps {
  onClose: () => void;
}

type ModalState = 'form' | 'loading' | 'success' | 'error';

export function ContactModal({ onClose }: ContactModalProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [state, setState] = useState<ModalState>('form');
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstInputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const isValidEmail = (v: string) => /[^@]+@[^@]+\.[^@]+/.test(v);
  const canSubmit = name.trim() && isValidEmail(email) && message.trim().length >= 10;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setState('loading');
    try {
      await submitContact({ name: name.trim(), email: email.trim(), message: message.trim() });
      setState('success');
    } catch {
      setState('error');
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 px-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl p-7">
        {state === 'success' ? (
          <div className="text-center py-6">
            <div className="text-4xl mb-4">✓</div>
            <h2 className="text-lg font-semibold text-gray-900 font-serif mb-2">Message sent</h2>
            <p className="text-sm text-gray-500">Thanks for reaching out. I'll get back to you soon.</p>
            <button
              onClick={onClose}
              className="mt-6 border border-gray-300 rounded-md px-5 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Close
            </button>
          </div>
        ) : (
          <>
            <div className="flex justify-between items-start mb-5">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 font-serif">Contact the developer</h2>
                <p className="text-sm text-gray-500 mt-1">Questions, feedback, or bug reports welcome.</p>
              </div>
              <button onClick={onClose} aria-label="Close" className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-4">✕</button>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <label htmlFor="contact-name" className="block text-xs font-medium text-gray-700 mb-1">Name</label>
                <input
                  id="contact-name"
                  ref={firstInputRef}
                  type="text"
                  value={name}
                  onChange={(e) => { setName(e.target.value); if (state === 'error') setState('form'); }}
                  placeholder="Your name"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                  required
                />
              </div>
              <div>
                <label htmlFor="contact-email" className="block text-xs font-medium text-gray-700 mb-1">Email</label>
                <input
                  id="contact-email"
                  type="email"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); if (state === 'error') setState('form'); }}
                  placeholder="your@email.com"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                  required
                />
              </div>
              <div>
                <label htmlFor="contact-message" className="block text-xs font-medium text-gray-700 mb-1">Message</label>
                <textarea
                  id="contact-message"
                  value={message}
                  onChange={(e) => { setMessage(e.target.value); if (state === 'error') setState('form'); }}
                  placeholder="What's on your mind?"
                  rows={4}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
                  required
                />
              </div>

              {state === 'error' && (
                <p className="text-sm text-red-600">
                  Something went wrong — please try again or email{' '}
                  <a href="mailto:pcaisearch@atomicmail.io" className="underline">pcaisearch@atomicmail.io</a> directly.
                </p>
              )}

              <button
                type="submit"
                disabled={!canSubmit || state === 'loading'}
                className="bg-[#2c1f14] text-white rounded-md py-2.5 text-sm font-medium hover:bg-[#3d2d1e] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {state === 'loading' ? 'Sending…' : 'Send message'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
