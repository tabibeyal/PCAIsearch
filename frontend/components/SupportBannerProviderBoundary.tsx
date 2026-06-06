'use client';

import { SupportBannerProvider } from './SupportBannerContext';

// Establishes the 'use client' boundary so the async server component
// (app/search/[query]/page.tsx) can stay server-rendered. All descendants
// that need the support banner context must live inside this wrapper.
export function SupportBannerProviderBoundary({ children }: { children: React.ReactNode }) {
  return <SupportBannerProvider>{children}</SupportBannerProvider>;
}
