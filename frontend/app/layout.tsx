import type { Metadata, Viewport } from 'next'
import './globals.css'

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  interactiveWidget: 'resizes-content',
}

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
      <body className="antialiased flex flex-col h-dvh overflow-hidden">
        <main className="flex-1 min-h-0">{children}</main>
      </body>
    </html>
  )
}
