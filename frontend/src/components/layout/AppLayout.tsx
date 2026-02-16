import { ReactNode } from 'react'
import Header from './Header'

interface AppLayoutProps {
  children: ReactNode
  onNavigate: (path: string) => void
}

export default function AppLayout({ children, onNavigate }: AppLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      <Header onNavigate={onNavigate} />
      <main className="flex-1 p-4 max-w-5xl mx-auto w-full">
        {children}
      </main>
    </div>
  )
}
