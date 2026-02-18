import { ReactNode } from 'react'
import Header from './Header'

interface AppLayoutProps {
  children: ReactNode
  onNavigate: (path: string) => void
}

export default function AppLayout({ children, onNavigate }: AppLayoutProps) {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header onNavigate={onNavigate} />
      <main className="flex-1 min-h-0">
        {children}
      </main>
    </div>
  )
}
