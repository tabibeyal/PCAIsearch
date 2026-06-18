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
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    dialogRef.current?.showModal();
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

  const inputClass =
    'w-full border border-[#e8e4dc] rounded-md px-3 py-2 text-sm text-[#2c1f14] placeholder-[#76604a] bg-white focus:outline-none focus:border-[#9c8c7a] focus:ring-2 focus:ring-[#9c8c7a] transition-colors';
  const labelClass = 'block text-xs font-medium text-[#2c1f14] mb-1';

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-[100] m-auto w-full max-w-md rounded-xl border border-[#e8e4dc] bg-white shadow-lg p-7 backdrop:bg-black/40 open:flex open:flex-col"
      onClick={(e) => { if (e.target === dialogRef.current) onClose(); }}
      onClose={onClose}
    >
      {state === 'success' ? (
        <div className="text-center py-6">
          <div className="text-4xl mb-4 text-[#4a3728]">✓</div>
          <h2 className="text-lg font-semibold text-[#2c1f14] font-serif mb-2">Message sent</h2>
          <p className="text-sm text-[#76604a]">Thanks for reaching out. I&apos;ll get back to you soon.</p>
          <button
            onClick={onClose}
            className="mt-6 border border-[#e8e4dc] text-[#6b4e35] rounded-md px-5 py-2 text-sm hover:bg-[#ede8df] transition-colors"
          >
            Close
          </button>
        </div>
      ) : (
        <>
          <div className="flex justify-between items-start mb-5">
            <div>
              <h2 className="text-lg font-semibold text-[#2c1f14] font-serif">Contact the developer</h2>
              <p className="text-sm text-[#76604a] mt-1">Questions, feedback, or bug reports welcome.</p>
            </div>
            <button onClick={onClose} aria-label="Close" className="text-[#76604a] hover:text-[#4a3728] text-xl leading-none ml-4">✕</button>
          </div>

          <form method="dialog" onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label htmlFor="contact-name" className={labelClass}>Name</label>
              <input
                id="contact-name"
                ref={firstInputRef}
                type="text"
                value={name}
                onChange={(e) => { setName(e.target.value); if (state === 'error') setState('form'); }}
                placeholder="Your name"
                className={inputClass}
                required
              />
            </div>
            <div>
              <label htmlFor="contact-email" className={labelClass}>Email</label>
              <input
                id="contact-email"
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); if (state === 'error') setState('form'); }}
                placeholder="your@email.com"
                className={inputClass}
                required
              />
            </div>
            <div>
              <label htmlFor="contact-message" className={labelClass}>Message</label>
              <textarea
                id="contact-message"
                value={message}
                onChange={(e) => { setMessage(e.target.value); if (state === 'error') setState('form'); }}
                placeholder="What's on your mind?"
                rows={4}
                className={`${inputClass} resize-none`}
                required
              />
            </div>

            {state === 'error' && (
              <p className="text-sm text-red-800">
                Something went wrong — please try again or email{' '}
                <a href="mailto:pcaisearch@atomicmail.io" className="underline">pcaisearch@atomicmail.io</a> directly.
              </p>
            )}

            <button
              type="submit"
              disabled={!canSubmit || state === 'loading'}
              className="bg-[#4a3728] text-white rounded-md py-2.5 text-sm font-medium hover:bg-[#6b4e35] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {state === 'loading' ? 'Sending…' : 'Send message'}
            </button>
          </form>
        </>
      )}
    </dialog>
  );
}