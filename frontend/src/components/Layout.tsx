import { ReactNode } from 'react'
import Sidebar from './Sidebar'
import AlertBanner from './AlertBanner'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen bg-background overflow-hidden relative">
      {/* Animated background gradient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-background/95" />
        <div className="absolute top-0 left-0 w-1/2 h-1/2 bg-gradient-radial from-primary/5 to-transparent blur-3xl" />
        <div className="absolute bottom-0 right-0 w-1/2 h-1/2 bg-gradient-radial from-success/5 to-transparent blur-3xl" />
      </div>
      
      <Sidebar />
      
      <div className="flex-1 flex flex-col overflow-hidden relative z-10">
        <AlertBanner />
        <main className="flex-1 overflow-y-auto p-6 relative">
          <div className="max-w-[1920px] mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
