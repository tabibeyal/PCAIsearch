'use client';

import React, { createContext, useContext, useMemo, useState } from 'react';

interface SupportBannerContextValue {
  deepDiveOpen: boolean;
  setDeepDiveOpen: (open: boolean) => void;
}

const SupportBannerContext = createContext<SupportBannerContextValue | null>(null);

export function SupportBannerProvider({ children }: { children: React.ReactNode }) {
  const [deepDiveOpen, setDeepDiveOpen] = useState(false);
  const value = useMemo(() => ({ deepDiveOpen, setDeepDiveOpen }), [deepDiveOpen]);
  return <SupportBannerContext.Provider value={value}>{children}</SupportBannerContext.Provider>;
}

export function useSupportBanner(): SupportBannerContextValue {
  const ctx = useContext(SupportBannerContext);
  if (!ctx) {
    throw new Error('useSupportBanner must be used inside <SupportBannerProvider>');
  }
  return ctx;
}
