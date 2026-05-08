import type { Metadata } from 'next'
import './globals.css'

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
      <body className="antialiased">{children}</body>
    </html>
  )
}
