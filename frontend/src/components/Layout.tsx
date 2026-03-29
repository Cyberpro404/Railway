import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import AlertBanner from './AlertBanner'
import ConnectionStatus from './ConnectionStatus'

export default function Layout() {
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
        <div className="flex items-center justify-between p-4 border-b border-border/20">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-text">Gandiva Pro</h1>
            <span className="text-sm text-text-muted">Railway Monitoring System</span>
          </div>
          <ConnectionStatus />
        </div>
        <AlertBanner />
        <main className="flex-1 overflow-y-auto p-6 relative">
          <div className="max-w-[1920px] mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
