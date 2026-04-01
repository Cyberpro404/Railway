import { NavLink, useLocation } from 'react-router-dom'
import {
  Wifi,
  Brain,
  AlertTriangle,
  Settings,
  Activity,
  Zap,
  FileText,
  Train,
  Search,
  Clock,
  Server
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '@/lib/websocket'

const tabs = [
  { path: '/', label: 'Overview', icon: Activity, color: 'text-primary', description: 'Executive summary' },
  { path: '/live', label: 'Live Monitoring', icon: Zap, color: 'text-success', description: 'Real-time feeds' },
  { path: '/fleet', label: 'Fleet Status', icon: Train, color: 'text-primary', description: 'All coaches view' },
  { path: '/defects', label: 'Defect Analysis', icon: Search, color: 'text-warning', description: 'Diagnostics' },
  { path: '/history', label: 'Historical Data', icon: Clock, color: 'text-primary', description: 'Trends & playback' },
  { path: '/alerts', label: 'Alerts & Events', icon: AlertTriangle, color: 'text-critical', description: 'Notifications' },
  { path: '/reports', label: 'Reports', icon: FileText, color: 'text-primary', description: 'Downloads' },
  { path: '/devices', label: 'Connection Management', icon: Wifi, color: 'text-success', description: 'Manage DXMs & Network' },
  { path: '/settings', label: 'Configuration', icon: Settings, color: 'text-text-muted', description: 'Admin calibration' },
]

export default function Sidebar() {
  const [connectionStatus, setConnectionStatus] = useState(false)
  const [hasAlerts, setHasAlerts] = useState(false)
  const [sensorData, setSensorData] = useState<any>(null)
  const location = useLocation()

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((data: WebSocketData) => {
      setConnectionStatus(data.connection_status?.connected || false)
      setSensorData(data.sensor_data)
      if (data.ml_prediction?.class === 1 && data.ml_prediction.confidence > 0.3) {
        setHasAlerts(true)
      }
    })
    return unsubscribe
  }, [])

  return (
    <aside className="w-64 bg-background border-r border-border flex flex-col shadow-xl relative overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-border relative z-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded bg-card border border-primary">
            <Train className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-wider text-text uppercase">
              Project Gandhiva
            </h1>
            <p className="text-[10px] text-text-muted font-medium uppercase tracking-widest">Team Partha</p>
          </div>
        </div>

        {/* Live Status Card */}
        <div className="mt-4 p-3 rounded bg-card border border-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-text-muted">System Status</span>
            <div className={cn(
              "flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold",
              connectionStatus 
                ? "bg-success/20 text-success" 
                : "bg-border/50 text-text-muted"
            )}>
              <div className={cn(
                "w-1.5 h-1.5 rounded-full",
                connectionStatus ? "bg-success" : "bg-text-muted"
              )}>
                {connectionStatus && (
                  <div className="absolute w-1.5 h-1.5 rounded-full bg-success animate-ping" />
                )}
              </div>
              {connectionStatus ? 'ONLINE' : 'OFFLINE'}
            </div>
          </div>
          
          {sensorData && (
            <div className="grid grid-cols-2 gap-2 mt-2">
              <div className="bg-background rounded px-2 py-1.5 border border-border">
                <div className="text-[9px] text-text-muted uppercase font-semibold">Vibration</div>
                <div className="text-xs font-bold text-primary">{sensorData.z_rms?.toFixed(2)} mm/s</div>
              </div>
              <div className="bg-background rounded px-2 py-1.5 border border-border">
                <div className="text-[9px] text-text-muted uppercase font-semibold">Temp</div>
                <div className="text-xs font-bold text-warning">{sensorData.temperature?.toFixed(1)}°C</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto relative z-10">
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
                  "group flex items-center gap-3 px-3 py-2.5 rounded transition-all duration-200",
                  "relative overflow-hidden",
                  active
                    ? "bg-primary/10 text-primary border border-primary/30"
                    : "text-text-muted hover:text-text hover:bg-card border border-transparent"
                )
              }
            >
              <div className={cn(
                "flex items-center justify-center w-8 h-8 rounded transition-all duration-200",
                isActive 
                  ? "bg-primary/10" 
                  : "bg-card group-hover:bg-border"
              )}>
                <Icon className={cn(
                  "w-4 h-4 transition-all duration-200",
                  tab.color
                )} />
              </div>

              <div className="flex-1">
                <div className="text-sm font-semibold">
                  {tab.label}
                </div>
                {!isActive && (
                  <div className="text-[10px] text-text-muted opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    {tab.description}
                  </div>
                )}
              </div>

              {/* Alert badge */}
              {isAlertTab && hasAlerts && (
                <div className="relative">
                  <div className="w-2 h-2 rounded-full bg-critical" />
                  <div className="absolute inset-0 w-2 h-2 rounded-full bg-critical animate-ping opacity-75" />
                </div>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border relative z-10">
        <div className="text-[10px] text-text-muted text-center uppercase tracking-widest">
          <div className="font-semibold text-primary/50">v4.1.0-SCADA</div>
          <div className="text-text-muted mt-0.5">© 2026 Team Partha</div>
        </div>
      </div>
    </aside>
  )
}

