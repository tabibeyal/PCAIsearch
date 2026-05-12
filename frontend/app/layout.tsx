import type { Metadata } from 'next'
import './globals.css'
import { SupportBanner } from '@/components/SupportBanner'

export const metadata: Metadata = {
  title: 'Ask the Pali Canon',
  description: 'Type a question or topic — find the suttas that answer it.',
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
