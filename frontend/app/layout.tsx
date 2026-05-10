import type { Metadata } from 'next'
import './globals.css'
import { SupportBanner } from '@/components/SupportBanner'

export const metadata: Metadata = {
  title: 'Pali Canon AI Search',
  description: 'High-fidelity semantic search for the Pali Canon',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased flex flex-col min-h-screen" suppressHydrationWarning>
        <main className="flex-1">{children}</main>
        <SupportBanner />
      </body>
    </html>
  )
}
