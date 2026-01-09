import { NavLink, useLocation } from 'react-router-dom'
import { 
  Wifi, 
  BarChart3, 
  TrendingUp, 
  Brain, 
  Database, 
  FileText, 
  AlertTriangle, 
  Settings, 
  Sliders,
  Sparkles
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '@/lib/websocket'

const tabs = [
  { path: '/connection', label: 'CONNECTION STATUS', icon: Wifi, color: 'text-primary' },
  { path: '/executive', label: 'EXECUTIVE DASHBOARD', icon: BarChart3, color: 'text-success' },
  { path: '/analytics', label: 'HEALTH ANALYTICS', icon: TrendingUp, color: 'text-warning' },
  { path: '/ml', label: 'ML INTELLIGENCE', icon: Brain, color: 'text-primary' },
  { path: '/data', label: 'DATA MANAGEMENT', icon: Database, color: 'text-success' },
  { path: '/logs', label: 'OPERATION LOGS', icon: FileText, color: 'text-text-muted' },
  { path: '/alerts', label: 'ACTIVE ALERTS', icon: AlertTriangle, color: 'text-critical' },
  { path: '/thresholds', label: 'THRESHOLDS', icon: Sliders, color: 'text-warning' },
  { path: '/control', label: 'SYSTEM CONTROL', icon: Settings, color: 'text-primary' },
]

export default function Sidebar() {
  const [connectionStatus, setConnectionStatus] = useState(false)
  const [hasAlerts, setHasAlerts] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((data: WebSocketData) => {
      setConnectionStatus(data.connection_status?.connected || false)
      if (data.ml_prediction?.class === 1 && data.ml_prediction.confidence > 0.3) {
        setHasAlerts(true)
      }
    })
    return unsubscribe
  }, [])

  return (
    <aside className="w-72 glassmorphism-dark border-r border-border/50 flex flex-col shadow-2xl relative overflow-hidden">
      {/* Animated background particles */}
      <div className="particle-bg absolute inset-0 opacity-30 pointer-events-none" />
      
      {/* Header with enhanced styling */}
      <div className="p-6 border-b border-border/30 relative z-10">
        <div className="flex items-center gap-3 mb-2">
          <div className="relative">
            <div className="w-3 h-3 rounded-full bg-primary pulse-ring" />
            <div className="absolute inset-0 w-3 h-3 rounded-full bg-primary animate-ping opacity-75" />
          </div>
          <h1 className="text-2xl font-bold text-gradient-primary tracking-tight">
            GANDIVA PRO
          </h1>
          <Sparkles className="w-4 h-4 text-primary float-animation" />
        </div>
        <p className="text-xs text-text-muted mt-2 font-semibold opacity-80">
          Railway Condition Monitoring
        </p>
        
        {/* Connection status with animation */}
        <div className="mt-4 p-3 rounded-lg bg-background/30 border border-border/30">
          <div className="flex items-center gap-2">
            <div className={cn(
              "relative w-2.5 h-2.5 rounded-full",
              connectionStatus ? "bg-success" : "bg-text-muted"
            )}>
              {connectionStatus && (
                <>
                  <div className="absolute inset-0 rounded-full bg-success animate-ping opacity-75" />
                  <div className="absolute inset-0 rounded-full bg-success pulse-ring" />
                </>
              )}
            </div>
            <span className={cn(
              "text-xs font-bold uppercase tracking-wider",
              connectionStatus ? "text-success" : "text-text-muted"
            )}>
              {connectionStatus ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>
      
      {/* Navigation with enhanced animations */}
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto relative z-10">
        {tabs.map((tab, index) => {
          const Icon = tab.icon
          const isAlertTab = tab.path === '/alerts'
          const isActive = location.pathname === tab.path
          
          return (
            <NavLink
              key={tab.path}
              to={tab.path}
              className={({ isActive: active }) =>
                cn(
                  "flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all duration-300",
                  "relative group overflow-hidden",
                  "border border-transparent",
                  active 
                    ? "bg-gradient-to-r from-primary/20 to-primary/10 text-primary neon-glow border-primary/40 shadow-lg scale-105" 
                    : "text-text-muted hover:text-text hover:bg-card/40 hover:border-border/50 hover:scale-102"
                )
              }
              style={{ animationDelay: `${index * 0.05}s` }}
            >
              {/* Active indicator line */}
              {isActive && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-primary to-success rounded-r-full" />
              )}
              
              {/* Hover gradient effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-primary/0 via-primary/5 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              
              <Icon className={cn(
                "w-5 h-5 transition-all duration-300 relative z-10",
                "group-hover:scale-110 group-hover:rotate-3",
                isActive && "scale-110"
              )} />
              
              <span className="text-sm font-bold flex-1 relative z-10 tracking-wide">
                {tab.label}
              </span>
              
              {/* Alert badge */}
              {isAlertTab && hasAlerts && (
                <div className="relative z-10">
                  <div className="w-2.5 h-2.5 rounded-full bg-critical pulse-ring" />
                  <div className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-critical animate-ping opacity-75" />
                </div>
              )}
              
              {/* Active glow effect */}
              {isActive && (
                <div className="absolute inset-0 rounded-xl bg-primary/5 blur-xl" />
              )}
            </NavLink>
          )
        })}
      </nav>
      
      {/* Footer with enhanced styling */}
      <div className="p-4 border-t border-border/30 bg-background/40 backdrop-blur-sm relative z-10">
        <div className="text-xs text-text-muted space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="font-bold text-text">Version 4.0.0</span>
            <div className="w-1.5 h-1.5 rounded-full bg-success pulse-subtle" />
          </div>
          <div className="text-[10px] opacity-70 font-medium">
            AI-Designed Industrial UI
          </div>
        </div>
      </div>
    </aside>
  )
}
